from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import BackCallback, CancelPromoCodeCallback
from bot.enums import BackDestination
from core.models import PromoCode


def build_promo_kb(active_promo: PromoCode | None) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []

    if active_promo is not None:
        kb.append([InlineKeyboardButton("🚫 Отменить промокод", callback_data=CancelPromoCodeCallback())])

    kb.append([
        InlineKeyboardButton(
            "◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_PAYMENT)
        )
    ])

    return InlineKeyboardMarkup(kb)
