from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class KeyboardMethodError(Exception):
    """Базовая ошибка при создании клавиатуры для методов оплаты."""


def build_error_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)]])
