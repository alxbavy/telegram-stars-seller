from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.main import build_info_kb

async def show_info_page(update: Update):
    text = (
        "👜 <b>Информация</b>\n\n"
        "📄 Пользовательское соглашение:\nhttps://clck.su/ofertalame\n"
        "🔰 Политика конфиденциальности:\nhttps://clck.su/politikalame\n"
        "🌠 Отзывы:\nhttps://t.me/+MGPE9YDPigpkNDQy\n\n"
        "❓ Часто задаваемые вопросы:\nhttps://clck.su/faqlame"
    )
    await render_screen(update, text, build_info_kb(), "info.jpg")
