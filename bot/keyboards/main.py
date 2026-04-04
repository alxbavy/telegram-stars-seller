from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.callbacks import MainMenuCallback, MainMenuAction, BackCallback, BackDestination


def build_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data=MainMenuCallback(MainMenuAction.BUY))],
        [
            InlineKeyboardButton("👄 Поддержка", callback_data=MainMenuCallback(MainMenuAction.SUPPORT)),
            InlineKeyboardButton("👻 Мой профиль", callback_data=MainMenuCallback(MainMenuAction.PROFILE))
        ]
    ])

def build_support_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])
