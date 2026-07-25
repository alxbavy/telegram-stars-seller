from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from bot.callbacks import create_callback, RepeatOrderCallback


async def _get_stars_sent_kb_list(telegram_id: int, with_feedback: bool = True) -> list[list[InlineKeyboardButton]]:
    kb = [[InlineKeyboardButton(
        "✨ Сделать ещё заказ!",
        callback_data=await create_callback(telegram_id, RepeatOrderCallback())
    )]]

    if with_feedback:
        kb.append([InlineKeyboardButton("👛 Оставить отзыв", url="https://t.me/+MGPE9YDPigpkNDQy")])

    return kb


async def build_order_success_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(await _get_stars_sent_kb_list(telegram_id))


async def build_order_in_doubt_kb(telegram_id: int, support_url: str) -> InlineKeyboardMarkup:
    kb = await _get_stars_sent_kb_list(telegram_id)
    kb.append([InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)])
    return InlineKeyboardMarkup(kb)


async def build_order_canceled_kb(telegram_id: int, support_url: str) -> InlineKeyboardMarkup:
    kb = await _get_stars_sent_kb_list(telegram_id, with_feedback=False)
    kb.append([InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)])
    return InlineKeyboardMarkup(kb)
