from telegram import Update

from bot.keyboards.main import build_support_kb
from bot.renderers.base import render_screen


async def show_support_page(update: Update, support_url: str):
    text = "💬 <b>Нужна помощь?</b>\n\nАгент поддержки отвечает с 09:00 по 22:00 (МСК).\nПри высокой нагрузке ответ может занять немного больше времени."
    await render_screen(update, text, build_support_kb(support_url), "support.jpg")
