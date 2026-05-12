from telegram import Update, Message

from bot.renderers.base import render_screen
from bot.keyboards.main import build_main_menu_kb


async def show_main_menu(update: Update) -> Message:
    text = (
        "😍 <b>Ты не лэйм! Ты решил брать звёзды у нас — правильный выбор!</b>\n\n"
        "Звёзды <b>дешевле</b>, чем в самом <b>Telegram</b>!\n"
        "Бери себе или дари друзьям ;)"
    )
    return await render_screen(update, text, build_main_menu_kb(), "main_menu.jpg")
