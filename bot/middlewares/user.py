from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.injector import inject
from core.repositories.utils import db_action_with_tenacity
from core.services.user import UserService


@inject
async def _register_user_middleware_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        user_service: UserService
) -> None:
    tg_user = update.effective_user

    if not tg_user:
        return

    _ = await db_action_with_tenacity(user_service.register_user(
        telegram_id=tg_user.id,
        username=tg_user.username
    ))


async def register_user_middleware(update: type[Update], context: ContextTypes.DEFAULT_TYPE) -> None:
    await _register_user_middleware_helper(cast(Update, cast(object, update)), context)
