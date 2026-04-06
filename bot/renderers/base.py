import os
from django.conf import settings
from telegram import Update, InputMediaPhoto
from telegram.ext import ContextTypes


async def render_screen(update: Update, text: str, reply_markup, photo_name: str):
    """
    Универсальный рендерер.
    Пытается загрузить фото из локальной папки images/.
    Если файла нет, использует dummy_photo_url.
    """
    image_path = settings.BASE_DIR / 'images' / photo_name

    if image_path.exists() and image_path.is_file():
        media_source = open(image_path, 'rb')
    else:
        media_source = f"https://dummyimage.com/600x400/000/fff&text={photo_name}"

    try:
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_media(
                    media=InputMediaPhoto(media=media_source, caption=text),
                    reply_markup=reply_markup
                )
            except Exception:
                if hasattr(media_source, 'seek'):
                    media_source.seek(0)

                await update.effective_message.reply_photo(
                    photo=media_source,
                    caption=text,
                    reply_markup=reply_markup
                )
        else:
            await update.effective_message.reply_photo(
                photo=media_source,
                caption=text,
                reply_markup=reply_markup
            )
    finally:
        if hasattr(media_source, 'close') and callable(media_source.close):
            media_source.close()
