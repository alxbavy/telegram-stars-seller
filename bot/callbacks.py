import re
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4
from dataclasses import dataclass, asdict, field
from contextlib import asynccontextmanager
from abc import ABC, ABCMeta
from typing import cast, final, ClassVar
from collections.abc import AsyncGenerator

from telegram import CallbackQuery, Update
from telegram.ext import ConversationHandler

from general.utils import json_dumps, json_loads

from bot.enums import MainMenuAction, BackDestination, RecipientMode, ProfileAction

from core.services.redis_service import DecodingRedisDataError, get_async_redis_client


_MAIN_DOMAIN = "cb"
_BASE_CALLBACK = "BaseCallback"


def build_callback_key(callback_type_or_domain: type["BaseCallback"] | str, data_or_id: object | UUID | None) -> str:
    if isinstance(data_or_id, UUID):
        action_id = data_or_id
    elif data_or_id is not None:
        action_id = uuid4()
    else:
        action_id = None

    if isinstance(callback_type_or_domain, type):
        callback_domain = _REGISTRY[callback_type_or_domain]
    else:
        callback_domain = callback_type_or_domain

    return f"{_MAIN_DOMAIN}:{callback_domain}{':' + str(action_id) if action_id is not None else ''}"


def get_pattern(callback: type["BaseCallback"]) -> re.Pattern[str]:
    return re.compile(rf"^{build_callback_key(callback, None)}")


class CallbackRegistryMeta(ABCMeta):
    REGISTRY: dict[type["BaseCallback"], str] = {}
    INVERSE_REGISTRY: dict[str, type["BaseCallback"]] = {}

    def __new__(mcs, name: str, bases: tuple[type["BaseCallback"], ...], namespace: dict[str, object]):
        cls = super().__new__(mcs, name, bases, namespace)

        if name != _BASE_CALLBACK:  # проверяет, является ли текущий класс наследником (регистрировать базовый класс не нужно)
            cls = cast(type["BaseCallback"], cls)

            clean_name = name.lower()
            if clean_name.endswith("callback"):
                clean_name = clean_name[:-8]

            mcs.REGISTRY[cls] = clean_name
            mcs.INVERSE_REGISTRY[clean_name] = cls

            cls.pattern = get_pattern(cls)

        return cls


@dataclass(frozen=True, slots=True)
class BaseCallback(ABC, metaclass=CallbackRegistryMeta):
    pattern: ClassVar[re.Pattern[str]] = field(init=False)

    def __post_init__(self) -> None:
        all_slots: set[str] = {
            slot for cls in self.__class__.__mro__  # noqa  # слоты текущего класса и всех его родителей
            for slot in cast(tuple[str, ...], getattr(cls, "__slots__", ()))  # noqa
            if slot != "__weakref__"
        }

        for attr in all_slots:
            if not hasattr(self, attr):  # для необязательных полей
                continue

            value = cast(object, getattr(self, attr))

            if isinstance(value, str):
                try:
                    decimal_value = Decimal(value)
                    object.__setattr__(self, attr, decimal_value)

                except InvalidOperation:
                    continue


_REGISTRY = CallbackRegistryMeta.REGISTRY
_INVERSE_REGISTRY = CallbackRegistryMeta.INVERSE_REGISTRY


@dataclass(frozen=True, slots=True)
class CallbackKeyDTO:
    main_domain: str
    callback_domain: str
    action_id: UUID | None
    key: str = field(init=False)

    def __post_init__(self):
        if self.main_domain != _MAIN_DOMAIN:
            raise DecodingRedisDataError("Главный домен не совпал с доменом Callback")

        if self.callback_domain not in _INVERSE_REGISTRY.keys():
            raise DecodingRedisDataError("Домен колбэка не совпал с зарегистрированными Callback")

        key = build_callback_key(self.callback_domain, self.action_id)
        object.__setattr__(self, "key", key)


@dataclass(frozen=True, slots=True)
class RedisExpiredCallback:
    cb_key_dto: CallbackKeyDTO


def build_user_key(telegram_id: int) -> str:
    return f"user:{telegram_id}"


async def create_callback(telegram_id: int, callback: BaseCallback, /) -> str:
    data = asdict(callback)

    callback_key = build_callback_key(type(callback), data if data else None)

    if data:
        user_key = build_user_key(telegram_id)
        async_redis_client = get_async_redis_client()

        result = await async_redis_client.hset(name=user_key, key=callback_key, value=json_dumps(data))
        if not result:
            raise RuntimeError("Не получилось сохранить данные callback в Redis")

        result = await async_redis_client.expire(name=user_key, time=172800)
        if not result:
            raise RuntimeError("Не получилось установить TTL для данных callback в Redis")

    return callback_key


def validate_callback(raw_callback: str) -> CallbackKeyDTO | None:
    """
    - Если `cb_data` при `.split(":")` по длине не равна `2 или 3`, вернётся `None`, иначе
    вернётся `CallbackData`, у которого `action_id` может быть `None`.

    - Если структура запрашиваемого `Callback` из `Redis` не совпадает со структурой этого же `Callback` в коде,
    выбросится исключение `DecodingRedisDataError`.
    """

    callback_parts = raw_callback.split(":")
    callback_parts_len = len(callback_parts)

    if callback_parts_len == 2:
        return CallbackKeyDTO(main_domain=callback_parts[0], callback_domain=callback_parts[1], action_id=None)

    if callback_parts_len == 3:
        return CallbackKeyDTO(
            main_domain=callback_parts[0],
            callback_domain=callback_parts[1],
            action_id=UUID(callback_parts[2])
        )

    return None


async def parse_callback(
        telegram_id: int, raw_callback: str
) -> tuple[BaseCallback, CallbackKeyDTO] | RedisExpiredCallback | None:
    """
    - Если `raw_cb_data` при `.split(":")` по длине не равна `2 или 3`, вернётся `None`.

    - Если прошло `>2 суток` с момента создания записи о `Callback`, данных может не оказаться в `Redis`, тогда вернётся
    `RedisExpiredCallback`.

    - Если структура запрашиваемого `Callback` из `Redis` не совпадает со структурой этого же `Callback` в коде,
    выбросится исключение `DecodingRedisDataError`.

    - В иных случаях вернётся `BaseCallback`.
    """

    cb_key_dto = validate_callback(raw_callback)
    if cb_key_dto is None:
        return None

    callback_type = _INVERSE_REGISTRY[cb_key_dto.callback_domain]

    if cb_key_dto.action_id is not None:
        data = await (get_async_redis_client()).hget(build_user_key(telegram_id), cb_key_dto.key)
        if data is None:
            return RedisExpiredCallback(cb_key_dto)
        return json_loads(data, callback_type), cb_key_dto

    try:
        return callback_type(), cb_key_dto  # noqa

    except Exception as err:
        err_msg = "Произошла ошибка декодирования данных из Redis - скорее всего данные устарели"
        raise DecodingRedisDataError(err_msg) from err


async def parse_callback_force[T: BaseCallback](
        telegram_id: int, cb_query: CallbackQuery,
        callback_type: type[T]
) -> tuple[T | int, CallbackKeyDTO]:
    assert cb_query.data is not None

    parse_result = await parse_callback(telegram_id, cb_query.data)
    if parse_result is None:
        raise DecodingRedisDataError(f"Не получилось распарсить {callback_type.__name__}")
    if isinstance(parse_result, RedisExpiredCallback):
        _ = await cb_query.answer(text="Кнопка устарела, начни новый диалог /start", show_alert=True)
        return ConversationHandler.END, parse_result.cb_key_dto
    return cast(T, parse_result[0]), parse_result[1]  # noqa


async def delete_callback(telegram_id: int, cb_key_dto: CallbackKeyDTO) -> int | None:
    """Если нечего удалять (`cb_data.action_id is None`), вернётся `None`, иначе вернётся кол-во удалённых ключей."""
    if cb_key_dto.action_id is None:
        return None
    return await (get_async_redis_client()).hdel(build_user_key(telegram_id), cb_key_dto.key)


@asynccontextmanager
async def manage_callback_data[T: BaseCallback](
        update: Update, callback_type: type[T]
) -> AsyncGenerator[T | int, None]:
    user = update.effective_user
    cb_query = update.callback_query
    assert user is not None
    assert cb_query is not None

    cb_data, cb_key_dto = await parse_callback_force(user.id, cb_query, callback_type)
    yield cb_data

    if isinstance(cb_data, int) and cb_data != ConversationHandler.END:
        _ = await delete_callback(user.id, cb_key_dto)


@final
@dataclass(frozen=True, slots=True)
class MainMenuCallback(BaseCallback):
    action: MainMenuAction


@final
@dataclass(frozen=True, slots=True)
class BackCallback(BaseCallback):
    destination: BackDestination


@final
@dataclass(frozen=True, slots=True)
class SubscriptionCallback(BaseCallback):
    back_destination: BackDestination


@final
@dataclass(frozen=True, slots=True)
class ProfileMenuCallback(BaseCallback):
    action: ProfileAction


@final
@dataclass(frozen=True, slots=True)
class HistoryPageCallback(BaseCallback):
    page: int


@final
@dataclass(frozen=True, slots=True)
class FixedQuantityCallback(BaseCallback):
    amount: int


@final
@dataclass(frozen=True, slots=True)
class CustomQuantityCallback(BaseCallback): pass


@final
@dataclass(frozen=True, slots=True)
class RecipientModeCallback(BaseCallback):
    mode: RecipientMode


@final
@dataclass(frozen=True, slots=True)
class PaymentMethodCallback(BaseCallback):
    method_api: str
    method: str
    method_external_id: str
    price: Decimal


@final
@dataclass(frozen=True, slots=True)
class PromoCodeCallback(BaseCallback): pass


@final
@dataclass(frozen=True, slots=True)
class CancelPromoCodeCallback(BaseCallback): pass


@final
@dataclass(frozen=True, slots=True)
class OrderConfirmedCallback(BaseCallback): pass


@final
@dataclass(frozen=True, slots=True)
class RepeatOrderCallback(BaseCallback): pass


# @dataclass(frozen=True, slots=True)
# class ReferralsPageCallback:  # TODO: referrals
#     page: int
#
#
# @dataclass(frozen=True, slots=True)
# class ReferralDetailsCallback:
#     ref_user_id: int
#     page: int = 1
#
#
# @dataclass(frozen=True, slots=True)
# class ReferralPurchasesPageCallback:
#     ref_user_id: int
#     page: int
