from functools import wraps
from inspect import signature
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

from dishka import AsyncContainer
from dishka.exceptions import NoFactoryError

from bot.utils.type_aliases import UpdateWithContextHandler, ContextHandler, UpdateHandler, AsyncCallable


def inject[**P,R](func: UpdateWithContextHandler[P,R]):
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: ..., **kwargs: ...
    ) -> R:
        container = cast(AsyncContainer, context.bot_data["dishka_container"])
        return await _inject_parameters(container, func, [update, context], *args, **kwargs)

    return wrapper


def inject_without_update[**P,R](func: ContextHandler[P,R]):
    @wraps(func)
    async def wrapper(
            context: ContextTypes.DEFAULT_TYPE,
            *args: ..., **kwargs: ...
    ) -> R:
        container = cast(AsyncContainer, context.bot_data["dishka_container"])
        return await _inject_parameters(container, func, [context], *args, **kwargs)

    return wrapper


def inject_without_context[**P,R](func: UpdateHandler[P,R]):
    @wraps(func)
    async def wrapper(
            update: Update, context: ContextTypes.DEFAULT_TYPE,
            *args: ..., **kwargs: ...
    ) -> R:
        container = cast(AsyncContainer, context.bot_data["dishka_container"])
        return await _inject_parameters(container, func, [update], *args, **kwargs)

    return wrapper


async def _inject_parameters[**P,R](
        async_container: AsyncContainer,
        func: AsyncCallable[...,R],
        arbitrary_args: list[object], *args: P.args, **kwargs: P.kwargs
) -> R:
    print(func.__qualname__)

    async with async_container() as request_container:
        sig = signature(func)
        for name, param in sig.parameters.items():
            if name not in ("update", "context") and param.annotation is not param.empty:
                try:
                    kwargs[name] = await request_container.get(param.annotation)
                except NoFactoryError:
                    pass
        all_args = arbitrary_args + list(args)

        return await func(*all_args, **kwargs)
