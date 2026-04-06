import os
from django.conf import settings
from telegram import Update, InputMediaPhoto
from telegram.constants import ParseMode


async def render_screen(update: Update, text: str, reply_markup, photo_name: str = None):
    media_source = None
    if photo_name:
        image_path = settings.BASE_DIR / 'images' / photo_name
        media_source = open(image_path, 'rb') if image_path.exists() else f"https://dummyimage.com/600x400/000/fff&text={photo_name}"

    try:
        if update.callback_query:
            await update.callback_query.answer()
            try:
                if media_source:
                    await update.callback_query.edit_message_media(
                        media=InputMediaPhoto(media=media_source, caption=text, parse_mode=ParseMode.HTML),
                        reply_markup=reply_markup
                    )
                else:
                    await update.callback_query.edit_message_text(
                        text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
                    )
                return
            except Exception:
                try:
                    await update.effective_message.delete()
                except Exception:
                    pass

                if hasattr(media_source, 'seek'):
                    media_source.seek(0)

        kwargs = {"reply_markup": reply_markup, "parse_mode": ParseMode.HTML}
        if media_source:
            await update.effective_message.reply_photo(photo=media_source, caption=text, **kwargs)
        else:
            await update.effective_message.reply_text(text=text, **kwargs)

    finally:
        if hasattr(media_source, 'close') and callable(media_source.close):
            media_source.close()