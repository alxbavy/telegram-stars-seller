from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.callbacks import BackCallback, BackDestination, ProfileMenuCallback, ProfileAction, HistoryPageCallback


def build_profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 История заказов", callback_data=ProfileMenuCallback(ProfileAction.HISTORY)),
        ],[InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])


def build_order_history_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav_buttons = []

    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=HistoryPageCallback(page - 1)))

    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=HistoryPageCallback(page + 1)))

    keyboard = []
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("◀️ Назад в профиль", callback_data=BackCallback(BackDestination.PROFILE))])

    return InlineKeyboardMarkup(keyboard)
