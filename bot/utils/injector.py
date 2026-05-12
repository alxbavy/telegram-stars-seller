from functools import wraps
from inspect import signature
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

from dishka import AsyncContainer

from bot.utils.type_aliases import UpdateWithContextHandler


def inject[**P,R](func: UpdateWithContextHandler[...,R]):
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: P.args, **kwargs: P.kwargs
    ) -> R:
        container = cast(AsyncContainer, context.bot_data["dishka_container"])

        async with container() as request_container:
            sig = signature(func)
            for name, param in sig.parameters.items():
                if name not in ("update", "context") and param.annotation is not param.empty:
                    kwargs[name] = await request_container.get(param.annotation)

            return await func(update, context, *args, **kwargs)

    return wrapper