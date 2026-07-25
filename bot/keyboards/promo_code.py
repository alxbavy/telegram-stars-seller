from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import BackCallback, CancelPromoCodeCallback, create_callback
from bot.enums import BackDestination

from core.models import PromoCode


async def build_promo_kb(telegram_id: int, active_promo: PromoCode | None) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []

    if active_promo is not None:
        kb.append([InlineKeyboardButton(
            "🚫 Отменить промокод",
            callback_data=await create_callback(telegram_id, CancelPromoCodeCallback())
        )])

    kb.append([
        InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.CHOOSE_PAYMENT))
        )
    ])

    return InlineKeyboardMarkup(kb)
