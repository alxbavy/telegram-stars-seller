from telegram import Update, Message

from bot.keyboards.main import build_support_kb
from bot.renderers.base import render_screen
from bot.utils.active_conversation import autosave_active_conversation


@autosave_active_conversation
async def show_support_page(update: Update,support_url: str) -> Message:
    text = ("💬 <b>Нужна помощь?</b>\n\nАгент поддержки отвечает с 09:00 по 22:00 (МСК).\n"
            "При высокой нагрузке ответ может занять немного больше времени.")
    return await render_screen(update, text, build_support_kb(support_url), "support.jpg")
