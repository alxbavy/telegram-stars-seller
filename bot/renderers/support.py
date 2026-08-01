from telegram import Update, Message

from bot.enums import BackDestination
from bot.keyboards.support import SupportCallbackCreationData, build_support_kb
from bot.renderers.base import render_screen
from bot.utils.active_conversation import autosave_active_conversation


@autosave_active_conversation
async def show_support_page(update: Update,support_url: str) -> Message:
    text = (
        "💬 <b>Нужна помощь?</b>\n\n"
        "Агент поддержки отвечает с 09:00 по 22:00 (МСК).\n"
        "При высокой нагрузке ответ может занять немного больше времени"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_support_kb(
            support_url,
            SupportCallbackCreationData(
                telegram_id=update.effective_user.id,
                back_destination=BackDestination.MAIN_MENU
            )
        ),
        photo_name="support.jpg"
    )
