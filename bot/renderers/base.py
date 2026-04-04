from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes


async def render_screen(update: Update, text: str, reply_markup, photo_name: str):
    """Универсальный рендерер. Отправляет фото или редактирует текущее."""
    # В реальном проекте photo_name мапится на file_id из БД или URL
    dummy_photo_url = f"https://dummyimage.com/600x400/000/fff&text={photo_name}"

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_media(
                media=InputMediaPhoto(media=dummy_photo_url, caption=text),
                reply_markup=reply_markup
            )
        except Exception:
            # Фолбэк, если сообщение было без фото
            await update.effective_message.reply_photo(
                photo=dummy_photo_url, caption=text, reply_markup=reply_markup
            )
    else:
        await update.effective_message.reply_photo(
            photo=dummy_photo_url, caption=text, reply_markup=reply_markup
        )
