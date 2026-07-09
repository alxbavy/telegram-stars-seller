from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import BackCallback, CancelPromoCodeCallback
from bot.enums import BackDestination
from core.models import PromoCode


def build_promo_kb(is_self: bool, active_promo: PromoCode | None) -> InlineKeyboardMarkup:
    if is_self:
        back_dest = BackDestination.CHOOSE_PAYMENT_SELF
    else:
        back_dest = BackDestination.CHOOSE_PAYMENT_GIFT

    kb: list[list[InlineKeyboardButton]] = []

    if active_promo is not None:
        kb.append([InlineKeyboardButton("🚫 Отменить промокод", callback_data=CancelPromoCodeCallback())])

    kb.append([InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))])

    return InlineKeyboardMarkup(kb)
