from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def build_error_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)]])
