import re
from decimal import Decimal
from uuid import UUID, uuid4
from dataclasses import dataclass, asdict
from functools import cached_property
from abc import ABC, ABCMeta
from typing import cast, TYPE_CHECKING

from general_utils import json_dumps, json_loads

from bot.enums import MainMenuAction, BackDestination, RecipientMode, ProfileAction

from core.services.redis_service import DecodingRedisDataError, get_async_redis_client


# TODO: переписать колбэки на колбэки редиса


class CallbackRegistryMeta(ABCMeta):
    REGISTRY: dict[type["BaseCallback"], str] = {}
    INVERSE_REGISTRY: dict[str, type["BaseCallback"]] = {}

    def __new__(mcs, name: str, bases: tuple[type["BaseCallback"], ...], namespace: dict[str, object]):
        cls = super().__new__(mcs, name, bases, namespace)

        if bases:  # проверяет, является ли текущий класс наследником (регистрировать базовый класс не нужно)
            cls = cast(type["BaseCallback"], cls)
            clean_name = name.lower()
            if clean_name.endswith("callback"):
                clean_name = clean_name[:-8]
            mcs.REGISTRY[cls] = clean_name
            mcs.INVERSE_REGISTRY[clean_name] = cls

        return cls


@dataclass(frozen=True)
class BaseCallback(ABC, metaclass=CallbackRegistryMeta):
    if TYPE_CHECKING:
        dummy_kwarg: object


_REGISTRY = CallbackRegistryMeta.REGISTRY
_INVERSE_REGISTRY = CallbackRegistryMeta.INVERSE_REGISTRY


_MAIN_DOMAIN = "cb"


@dataclass(frozen=True, slots=True)
class CallbackData:
    main_domain: str
    callback_domain: str
    action_id: UUID | None

    def __post_init__(self):
        if self.main_domain != _MAIN_DOMAIN:
            raise DecodingRedisDataError("Главный домен не совпал с доменом Callback")

        if self.callback_domain not in _INVERSE_REGISTRY.keys():
            raise DecodingRedisDataError("Домен колбэка не совпал с зарегистрированными Callback")

    @cached_property
    def key(self) -> str:
        return f"{self.main_domain}:{self.callback_domain}{':' + str(self.action_id) if self.action_id else ''}"


class RedisExpiredCallback: pass


def build_callback_key(callback_type: type[BaseCallback]) -> str:
    return f"{_MAIN_DOMAIN}:{_REGISTRY[callback_type]}"


def get_pattern(callback: type[BaseCallback]) -> re.Pattern[str]:
    return re.compile(rf"^{build_callback_key(callback)}")


def build_user_key(telegram_id: int) -> str:
    return f"user:{telegram_id}"


async def create_callback(telegram_id: int, callback: BaseCallback) -> str:
    callback_key = build_callback_key(type(callback))

    data = asdict(callback)
    if data:
        callback_key += f":{uuid4()}"
        user_key = build_user_key(telegram_id)
        async_redis_client = get_async_redis_client()

        result = await async_redis_client.hset(name=user_key, key=callback_key, value=json_dumps(data))
        if not result:
            raise RuntimeError("Не получилось сохранить данные callback в Redis")

        result = await async_redis_client.expire(name=user_key, time=172800)
        if not result:
            raise RuntimeError("Не получилось установить TTL для данных callback в Redis")

    return callback_key


def validate_callback(cb_data: str) -> CallbackData | None:
    """
    - Если `cb_data` при `.split(":")` по длине не равна `2 или 3`, вернётся `None`, иначе
    вернётся `CallbackData`, у которого `action_id` может быть `None`.

    - Если структура запрашиваемого `Callback` из `Redis` не совпадает со структурой этого же `Callback` в коде,
    выбросится исключение `DecodingRedisDataError`.
    """

    callback_parts = cb_data.split(":")
    callback_parts_len = len(callback_parts)

    if callback_parts_len == 2:
        return CallbackData(main_domain=callback_parts[0], callback_domain=callback_parts[1], action_id=None)

    if callback_parts_len == 3:
        return CallbackData(
            main_domain=callback_parts[0],
            callback_domain=callback_parts[1],
            action_id=UUID(callback_parts[2])
        )

    return None


async def parse_callback(telegram_id: int, raw_cb_data: str) -> BaseCallback | RedisExpiredCallback | None:
    """
    - Если `raw_cb_data` при `.split(":")` по длине не равна `2 или 3`, вернётся `None`.

    - Если прошло `>2 суток` с момента создания записи о `Callback`, данных может не оказаться в `Redis`, тогда вернётся
    `RedisExpiredCallback`.

    - Если структура запрашиваемого `Callback` из `Redis` не совпадает со структурой этого же `Callback` в коде,
    выбросится исключение `DecodingRedisDataError`.

    - В иных случаях вернётся `BaseCallback`.
    """

    cb_data = validate_callback(raw_cb_data)
    if cb_data is None:
        return None

    dataclass_args: dict[str, object] = {}

    if cb_data.action_id is not None:
        data = await (get_async_redis_client()).hget(build_user_key(telegram_id), cb_data.key)
        if data is None:
            return RedisExpiredCallback()
        dataclass_args = cast(dict[str, object], json_loads(data))

    callback_type = _INVERSE_REGISTRY[cb_data.callback_domain]
    try:
        return callback_type(**dataclass_args)

    except Exception as err:
        err_msg = "Произошла ошибка декодирования данных из Redis - скорее всего данные устарели"
        raise DecodingRedisDataError(err_msg) from err


async def delete_callback(telegram_id: int, cb_data: CallbackData) -> int | None:
    """Если нечего удалять (`cb_data.action_id is None`), вернётся `None`, иначе вернётся кол-во удалённых ключей."""
    if cb_data.action_id is None:
        return None
    return await (get_async_redis_client()).hdel(build_user_key(telegram_id), cb_data.key)


@dataclass(frozen=True)
class MainMenuCallback(BaseCallback):
    action: MainMenuAction


@dataclass(frozen=True)
class BackCallback(BaseCallback):
    destination: BackDestination


@dataclass(frozen=True)
class ProfileMenuCallback(BaseCallback):
    action: ProfileAction


@dataclass(frozen=True)
class HistoryPageCallback(BaseCallback):
    page: int


@dataclass(frozen=True)
class FixedQuantityCallback(BaseCallback):
    amount: int


@dataclass(frozen=True)
class CustomQuantityCallback(BaseCallback): pass


@dataclass(frozen=True)
class RecipientModeCallback(BaseCallback):
    mode: RecipientMode


@dataclass(frozen=True)
class PaymentMethodCallback(BaseCallback):
    method_api: str
    method: str
    method_external_id: str
    price: Decimal


@dataclass(frozen=True)
class PromoCodeCallback(BaseCallback): pass


@dataclass(frozen=True)
class CancelPromoCodeCallback(BaseCallback): pass


@dataclass(frozen=True)
class OrderConfirmedCallback(BaseCallback): pass


@dataclass(frozen=True)
class RepeatOrderCallback(BaseCallback): pass


# TODO: referrals
# @dataclass(frozen=True)
# class ReferralsPageCallback:
#     page: int
#
#
# @dataclass(frozen=True)
# class ReferralDetailsCallback:
#     ref_user_id: int
#     page: int = 1
#
#
# @dataclass(frozen=True)
# class ReferralPurchasesPageCallback:
#     ref_user_id: int
#     page: int
