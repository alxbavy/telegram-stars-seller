from telegram import Update, Message

from bot.renderers.base import render_screen, send_new_message
from bot.keyboards.main import build_main_menu_kb
from bot.utils.active_conversation import autosave_active_conversation


@autosave_active_conversation
async def show_main_menu(update: Update) -> Message:
    text = (
        "😍 <b>Ты не лэйм! Ты решил брать звёзды у нас — правильный выбор!</b>\n\n"
        "Звёзды <b>дешевле</b>, чем в самом <b>Telegram</b>!\n"
        "Бери себе или дари друзьям ;)"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_main_menu_kb(update.effective_user.id),
        photo_name="main_menu.jpg"
    )


async def send_empty_username_alert(update: Update) -> Message:
    text = (
        f"⚠️ <b>У тебя отсутствует username!</b>\n\n"
        f"Покупка звёзд для себя невозможна без наличия <b>username</b>, но ты можешь продолжить пользоваться ботом "
        f"и купить звёзды кому-нибудь в подарок (по <b>username</b>)\n\n"
        f"Как сделать себе <b>username</b>:\n"
        f"⚙️ Настройки -> 👤 Мой аккаунт -> @ Имя пользователя (не путать с Имя)"
    )
    return await send_new_message(update, text, reply_markup=None, photo_name=None)


# TODO: сделать проверку подписки на канал на каждом шаге (либо почти на каждом - продумать)
# TODO: добавить уведомления о новых заказах в админскую группу
# TODO: добавить конструктор рассылок в админскую группу
