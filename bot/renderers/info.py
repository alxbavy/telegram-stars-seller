from telegram import Update, Message

from bot.keyboards.info import build_info_kb
from bot.renderers.base import render_screen
from bot.utils.active_conversation import autosave_active_conversation


@autosave_active_conversation
async def show_info_page(update: Update) -> Message:
    text = (
        "👜 <b>Информация</b>\n\n"
        "📄 Пользовательское соглашение:\nhttps://clck.su/ofertalame\n"
        "🔰 Политика конфиденциальности:\nhttps://clck.su/politikalame\n"
        "🌠 Отзывы:\nhttps://t.me/+MGPE9YDPigpkNDQy\n\n"
        "❓ Часто задаваемые вопросы:\nhttps://clck.su/faqlame"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_info_kb(update.effective_user.id),
        photo_name="info.jpg"
    )
