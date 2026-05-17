from telegram import Update, Message

from bot.renderers.base import render_screen
from bot.keyboards.main import build_main_menu_kb
from bot.utils.active_conversation import autosave_active_conversation


@autosave_active_conversation
async def show_main_menu(update: Update) -> Message:
    text = (
        "😍 <b>Ты не лэйм! Ты решил брать звёзды у нас — правильный выбор!</b>\n\n"
        "Звёзды <b>дешевле</b>, чем в самом <b>Telegram</b>!\n"
        "Бери себе или дари друзьям ;)"
    )
    return await render_screen(update, text, build_main_menu_kb(), "main_menu.jpg")


async def send_empty_username_alert(update: Update) -> Message:
    text = (
        f"⚠️ У вас отсутствует <b>username</b>. Покупка звёзд для себя невозможна без наличия <b>username</b>, но вы "
        f"можете продолжить пользоваться ботом и купить звёзды кому-нибудь в подарок (по <b>username</b>).\n\n"
        f"Чтобы сделать себе <b>username</b>, можете сделать следующее:\n"
        f"⚙️ Настройки -> 👤 Мой аккаунт -> @ Имя пользователя (не путать с Имя)"
    )
    return await update.effective_user.send_message(text)
