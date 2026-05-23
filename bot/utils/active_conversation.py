from functools import wraps

from telegram import Message, Update
from telegram.ext import ContextTypes

from bot.context import get_view_context
from bot.utils.type_aliases import UpdateHandler, UpdateWithContextHandler


def ensure_use_active_conversation_with_callback[**P,R](func: UpdateWithContextHandler[P,R]):
    """
    Перед выполнением декорируемой функции будет выполнена проверка на то, что функция работает с тем меню,
    которое было сохранено в ViewContext().active_conversation, т.е. с самым последним отправленным меню от бота.

    Декорируемая функция обязана изначально иметь в своих аргументах::

        update: Update, context: ContextTypes.DEFAULT_TYPE
    """
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: P.args, **kwargs: P.kwargs
    ) -> R | None:
        ctx = get_view_context(context)
        if ctx.active_conversation is None or ctx.active_conversation != update.effective_message:
            _ = await update.callback_query.answer("Это сообщение неактуально", show_alert=True)
            return None
        return await func(update, context, *args, **kwargs)

    return wrapper


def autosave_active_conversation[**P](func: UpdateHandler[P, Message]):
    """
    После выполнения декорируемой функции её возвращаемое значение будет сохранено в
    соответствующий get_view_context().active_conversation.

    Декорируемая функция после применения декоратора будет иметь в своих аргументах::

        update: Update, context: ContextTypes.DEFAULT_TYPE
    """
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: P.args, **kwargs: P.kwargs
    ) -> Message:
        ctx = get_view_context(context)
        msg = await func(update, *args, **kwargs)
        ctx.active_conversation = msg
        return msg

    return wrapper


def autosave_active_conversation_with_context[**P](func: UpdateWithContextHandler[P, Message]):
    """
    После выполнения декорируемой функции её возвращаемое значение будет сохранено в
    соответствующий get_view_context().active_conversation.

    Декорируемая функция после применения декоратора будет иметь в своих аргументах::

        update: Update, context: ContextTypes.DEFAULT_TYPE
    """
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: P.args, **kwargs: P.kwargs
    ) -> Message:
        ctx = get_view_context(context)
        msg = await func(update, context, *args, **kwargs)
        ctx.active_conversation = msg
        return msg

    return wrapper
