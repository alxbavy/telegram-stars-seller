from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.injector import inject
from core.services.user import UserService


@inject
async def register_user_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE, user_service: UserService):
    tg_user = update.effective_user

    if not tg_user:
        return

    await user_service.register_user(
        telegram_id=tg_user.id,
        username=tg_user.username
    )
