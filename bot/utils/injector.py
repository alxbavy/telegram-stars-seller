from functools import wraps
from inspect import signature
from telegram import Update
from telegram.ext import ContextTypes
from dishka import AsyncContainer


def inject(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        container: AsyncContainer = context.bot_data["dishka_container"]

        async with container() as request_container:
            sig = signature(func)
            for name, param in sig.parameters.items():
                if name not in ("update", "context") and param.annotation is not param.empty:
                    kwargs[name] = await request_container.get(param.annotation)

            return await func(update, context, *args, **kwargs)

    return wrapper