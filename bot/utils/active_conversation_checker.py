from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes

from bot.context import get_view_context


def ensure_use_active_conversation_with_callback(func):
    """
    Функция обязана иметь в своих аргументах::

        update: Update, context: ContextTypes.DEFAULT_TYPE

    Перед выполнением декорируемой функции будет выполнена проверка на то, что функция работает с тем меню,
    которое было сохранено в ViewContext().active_conversation, т.е. с самым последним отправленным меню от бота.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        ctx = get_view_context(context)
        if ctx.active_conversation is None or ctx.active_conversation != update.effective_message:
            await update.callback_query.answer("Это сообщение неактуально", show_alert=True)
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper


# TODO: применить декоратор к функциям из renderers, и убрать повсеместные сохранения сообщений в контекст
def autosave_active_conversation(func):
    """
    Функция обязана иметь в своих аргументах::

        update: Update, context: ContextTypes.DEFAULT_TYPE

    После выполнения декорируемой функции её возвращаемое значение будет сохранено в
    соответствующий get_view_context().active_conversation.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        ctx = get_view_context(context)
        msg = await func(update, context, *args, **kwargs)
        ctx.active_conversation = msg
        return msg

    return wrapper
