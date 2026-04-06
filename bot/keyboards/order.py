from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.callbacks import (
    FixedQuantityCallback, CustomQuantityCallback, BackCallback, BackDestination,
    RecipientModeCallback, PaymentMethodCallback, ConfirmOrderCallback, RepeatOrderCallback
)
from bot.context import RecipientMode

def build_quantity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ 50 звёзд", callback_data=FixedQuantityCallback(50)),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])

def build_back_to_quantity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_QUANTITY))]])

def build_large_order_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CUSTOM_QUANTITY_INPUT))]
    ])

def build_recipient_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥰 Себе", callback_data=RecipientModeCallback(RecipientMode.SELF))],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_QUANTITY))]
    ])

def build_back_to_recipient_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_RECIPIENT))]])

def build_user_not_found_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Ввести снова", callback_data=BackCallback(BackDestination.ENTER_GIFT_USERNAME))],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_RECIPIENT))]
    ])

def build_payment_methods_kb(sbp_price: float, card_price: float, back_dest: BackDestination) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📲 СБП — {sbp_price} ₽", callback_data=PaymentMethodCallback("sbp"))],
        [InlineKeyboardButton(f"💳 Картой — {card_price} ₽", callback_data=PaymentMethodCallback("card"))],
        # -----------------------------------------------------------
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))]
    ])

def build_confirmation_kb(pay_url: str, back_dest: BackDestination, is_self: bool) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton("💳 Оплатить", url=pay_url)]]
    if is_self:
        pass
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))])
    return InlineKeyboardMarkup(buttons)

def build_repeat_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✨ Сделать ещё заказ!", callback_data=RepeatOrderCallback())]])
