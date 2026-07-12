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
        user_service: FromDishka[UserService]
) -> None:
    tg_user = update.effective_user

    if not tg_user:
        return

    _ = await db_action_with_tenacity(user_service.register_user(
        telegram_id=tg_user.id,
        username=tg_user.username
    ))


async def register_user_middleware(update: type[Update], _: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_user_middleware_helper(cast(Update, cast(object, update)))
