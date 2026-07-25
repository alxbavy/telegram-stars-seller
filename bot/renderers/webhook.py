from decimal import Decimal
from uuid import UUID
from dataclasses import dataclass
from typing import cast, final

from telegram import InlineKeyboardMarkup

from bot.keyboards.order import build_order_confirmed_kb
from bot.keyboards.support import build_support_kb
from bot.keyboards.webhook import build_order_canceled_kb, build_order_in_doubt_kb, build_order_success_kb
from bot.renderers.order import get_order_created_text

from core.domain.enums import TransactionStatus, PROCESSING_STATUSES, get_translation
from core.domain.type_aliases import AsyncCallable
from core.models import TARGET_SELF


@dataclass(frozen=True, slots=True)
class _MessageInfo:
    status: str
    amount_stars: int
    price: Decimal
    target_username: str
    telegram_id: int
    transaction_id: UUID | str
    pay_url: str
    promo_name: str
    promo_discount: Decimal | None
    support_url: str

    def __post_init__(self):
        if self.target_username != TARGET_SELF:
            object.__setattr__(self, "target_username", f"@{self.target_username.lstrip("@")}")


async def get_message_parts_for_status(
        status: TransactionStatus,
        amount_stars: int,
        price: Decimal,
        target_username: str,
        telegram_id: int,
        transaction_id: UUID | str,
        pay_url: str,
        promo_name: str, promo_discount: Decimal | None,
        support_url: str
) -> tuple[str, InlineKeyboardMarkup | None, str]:
    msg_info = _MessageInfo(
        status,
        amount_stars, price, target_username, telegram_id,
        transaction_id, pay_url,
        promo_name, promo_discount,
        support_url
    )
    msg_parts_getter = _MESSAGE_PARTS_REGISTRY[status]
    return await msg_parts_getter(msg_info)


async def _get_message_parts_for_success(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    text = (
        f"😊 <b>Заказ успешно доставлен!</b>\n\n"
        f"Пополнили — ⭐ {msg_info.amount_stars} звёзд\n"
        f"{
        f'Для кого 🎁 — {msg_info.target_username}\n' if msg_info.target_username != TARGET_SELF else ''
        }"
        f"🆔 ID заказа — <code>{msg_info.transaction_id}</code>\n\n"
        f"Спасибо за покупку! ❤️"
    )
    reply_markup = await build_order_success_kb(msg_info.telegram_id)
    photo = "delivery_success.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_pending(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    target_username = "" if msg_info.target_username == TARGET_SELF else msg_info.target_username
    text = get_order_created_text(
        msg_info.transaction_id,
        msg_info.amount_stars, msg_info.price,
        target_username,
        promo_name=msg_info.promo_name, promo_discount=msg_info.promo_discount
    )
    reply_markup = build_order_confirmed_kb(msg_info.pay_url)
    photo = "order_confirmed.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_processing_statuses(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    text = (
        f"😊 <b>Заказ обрабатывается...</b>\n\n"
        f"Пополняем — ⭐{msg_info.amount_stars}\n"
        f"{f'Для кого 🎁 — {msg_info.target_username}\n' if msg_info.target_username != TARGET_SELF else ''}"
        f"🆔 ID заказа — <code>{msg_info.transaction_id}</code>\n\n"
        f"Обработка может занять до 15 минут. Если ничего не придёт, обратись в тех. поддержку"
    )
    reply_markup = await build_support_kb(msg_info.support_url)
    photo = "delivery_in_process.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_in_doubt(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    text = (
        f"🔍 <b>Проверь чат Telegram</b>\n\n"
        f"Бот отправил звёзды, но не смог проверить, дошли ли они. "
        f"Если в течение 5 минут ничего не придёт, обратись в тех. поддержку\n\n"
        f"Пополняем — ⭐{msg_info.amount_stars}\n"
        f"{f'Для кого 🎁 — {msg_info.target_username}\n' if msg_info.target_username != TARGET_SELF else ''}"
        f"🆔 ID заказа — <code>{msg_info.transaction_id}</code>"
    )
    reply_markup = await build_order_in_doubt_kb(msg_info.telegram_id, msg_info.support_url)
    photo = "delivery_in_process.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_failed(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    text = (
        f"❌ <b>Произошла ошибка при переводе звёзд!</b>\n\n"
        f"Обратись в тех. поддержку с ID заказа\n\n"
        f"🆔 ID заказа: <code>{msg_info.transaction_id}</code>\n"
    )
    reply_markup = await build_order_in_doubt_kb(msg_info.telegram_id, msg_info.support_url)
    photo = "delivery_failed.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_cancelled(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    text = (
        f"⌛ <b>Время на оплату истекло</b>\n\n"
        f"❌ Платёж отменён\n"
        f"🆔 ID заказа: <code>{msg_info.transaction_id}</code>"
    )
    reply_markup = await build_order_canceled_kb(msg_info.telegram_id, msg_info.support_url)
    photo = "delivery_canceled.jpg"
    return text, reply_markup, photo


async def _get_message_parts_for_unknown(msg_info: _MessageInfo) -> tuple[str, InlineKeyboardMarkup, str]:
    status = get_translation(msg_info.status) if msg_info.status else 'НЕИЗВЕСТНО'
    text = (
        f"⚠️ <b>Твоему заказу был присвоен статус {status}</b>\n\n"
        f"🆔 ID заказа: <code>{msg_info.transaction_id}</code>"
    )
    reply_markup = await build_support_kb(msg_info.support_url)
    photo = "delivery_unknown.jpg"
    return text, reply_markup, photo


@final
class _MessagePartsRegistry:
    def __init__(self) -> None:
        self._registry: dict[TransactionStatus, AsyncCallable[...,...]] = {
            TransactionStatus.SUCCESS: _get_message_parts_for_success,
            TransactionStatus.PENDING: _get_message_parts_for_pending,
            TransactionStatus.IN_DOUBT: _get_message_parts_for_in_doubt,
            TransactionStatus.FAILED: _get_message_parts_for_failed,
            TransactionStatus.CANCELLED: _get_message_parts_for_cancelled,
        }
        for status in PROCESSING_STATUSES:
            self._registry[status] = _get_message_parts_for_processing_statuses

    def __getitem__(self, item: str) -> AsyncCallable[[_MessageInfo], tuple[str, InlineKeyboardMarkup | None, str]]:
        item = cast(TransactionStatus, item)
        return self._registry.get(item, _get_message_parts_for_unknown)


_MESSAGE_PARTS_REGISTRY = _MessagePartsRegistry()
