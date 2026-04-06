from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.main import build_main_menu_kb


async def show_main_menu(update: Update):
    text = (
        "😍 Ты не лэйм! Ты решил брать звёзды у нас — правильный выбор!\n\n"
        "Звёзды дешевле, чем в самом Telegram!\n"
        "Бери себе или дари друзьям ;)"
    )
    await render_screen(update, text, build_main_menu_kb(), "main_menu.png")
