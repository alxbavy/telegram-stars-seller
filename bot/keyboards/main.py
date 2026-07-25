from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import MainMenuCallback, BackCallback, create_callback
from bot.enums import MainMenuAction, BackDestination


async def build_main_menu_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "⭐ Купить звёзды",
            callback_data=await create_callback(telegram_id, MainMenuCallback(MainMenuAction.BUY))
        )],
        [
            InlineKeyboardButton(
                "👄 Поддержка",
                callback_data=await create_callback(telegram_id, MainMenuCallback(MainMenuAction.SUPPORT))
            ),
            InlineKeyboardButton(
                "👻 Мой профиль",
                callback_data=await create_callback(telegram_id, MainMenuCallback(MainMenuAction.PROFILE))
            )
        ],
        [InlineKeyboardButton(
            "👜 Информация",
            callback_data=await create_callback(telegram_id, MainMenuCallback(MainMenuAction.INFO))
        )]
    ])


async def build_back_to_main_menu_kb(telegram_id: int, support_url: str | None) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = []
    if support_url is not None:
        kb.append([InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)])
    kb.append([InlineKeyboardButton(
        "🏠 Главное меню",
        callback_data=await create_callback(telegram_id, BackCallback(BackDestination.MAIN_MENU))
    )])
    return InlineKeyboardMarkup(kb)
