from dataclasses import dataclass

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot.callbacks import create_callback, BackCallback
from bot.enums import BackDestination


@dataclass(frozen=True, slots=True)
class SupportCallbackCreationData:
    telegram_id: int
    back_destination: BackDestination


async def build_support_kb(
        support_url: str,
        callback_creation_data: SupportCallbackCreationData | None = None
) -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton("✍️ Связаться с поддержкой",url=support_url)]]

    if callback_creation_data is not None:
        kb.append([InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(
                callback_creation_data.telegram_id,
                BackCallback(callback_creation_data.back_destination)
            )
        )])

    return InlineKeyboardMarkup(kb)
