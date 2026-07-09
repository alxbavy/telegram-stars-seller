from telegram import InlineKeyboardMarkup, InlineKeyboardButton


class KeyboardMethodError(Exception):
    """Базовая ошибка при создании клавиатуры для методов оплаты."""


# Тут нельзя добавлять callback, так как эта клавиатура используется во внешнем процессе, где callback передавать нельзя
def build_support_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)]])
