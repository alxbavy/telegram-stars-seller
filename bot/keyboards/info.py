from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot.callbacks import create_callback, BackCallback
from bot.enums import BackDestination


async def build_info_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.MAIN_MENU))
        )]
    ])
