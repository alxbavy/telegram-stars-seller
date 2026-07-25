import logging

from telegram import Update
from telegram.constants import ChatType, ChatMemberStatus
from telegram.ext import ApplicationHandlerStop, ContextTypes

from django.conf import settings


logger = logging.getLogger(__name__)


async def enforce_private_chats_only_or_admin_chat(update: object, _: ContextTypes.DEFAULT_TYPE):
    if not isinstance(update, Update):
        return

    chat = update.effective_chat

    if not chat:
        return

    if chat.type == ChatType.PRIVATE:
        return

    if update.my_chat_member:
        status = update.my_chat_member.new_chat_member.status
        if status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            raise ApplicationHandlerStop()

    if chat.id != settings.ADMIN_CHAT_ID:
        try:
            logger.info(f"Обнаружен несанкционированный чат {chat.title} ({chat.id}). Попытка выхода...")
            if await chat.leave():
                logger.info("Выход из чата прошёл успешно!")
            else:
                logger.error(f"Не удалось выйти из чата {chat.id} по неизвестной причине (возможно сбой сети)")

        except Exception as exc:
            if "not a member" not in str(exc):
                logger.error(f"Не удалось выйти из чата {chat.id}: {exc}")

    raise ApplicationHandlerStop()
