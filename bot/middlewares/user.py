from typing import cast, overload

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes

from core.repositories.utils import db_action_with_tenacity
from core.services.user import UserService
from core.ioc import inject


@overload
async def _register_user_middleware_helper(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: Update
) -> None: ...


@inject
async def _register_user_middleware_helper(
        update: Update,
        *,
        user_service: FromDishka[UserService]  # noqa
) -> None:
    tg_user = update.effective_user
    chat = update.effective_chat

    if not tg_user or chat is None or chat.type != chat.PRIVATE:
        return

    _ = await db_action_with_tenacity(user_service.register_user, tg_user.id, tg_user.username)


async def register_user_middleware(update: type[Update], _: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_user_middleware_helper(cast(Update, cast(object, update)))
