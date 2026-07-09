from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.callbacks import MainMenuCallback, BackCallback
from bot.enums import MainMenuAction, BackDestination


def build_main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Купить звёзды", callback_data=MainMenuCallback(MainMenuAction.BUY))],
        [
            InlineKeyboardButton("👄 Поддержка", callback_data=MainMenuCallback(MainMenuAction.SUPPORT)),
            InlineKeyboardButton("👻 Мой профиль", callback_data=MainMenuCallback(MainMenuAction.PROFILE))
        ],
        [InlineKeyboardButton("👜 Информация", callback_data=MainMenuCallback(MainMenuAction.INFO))]
    ])

# TODO: распределить билдеры по своим файлам
def build_support_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])


def build_back_to_main_menu_kb(support_url: str | None) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []
    if support_url is not None:
        kb.append([InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)])
    kb.append([InlineKeyboardButton("🏠 Главное меню", callback_data=BackCallback(BackDestination.MAIN_MENU))])
    return InlineKeyboardMarkup(kb)


def build_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])
