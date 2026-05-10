from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from bot.context import get_view_context


def ensure_use_active_conversation_with_callback(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        ctx = get_view_context(context)
        if ctx.active_conversation is None or ctx.active_conversation != update.effective_message:
            await update.callback_query.answer("Это сообщение неактуально", show_alert=True)
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper
