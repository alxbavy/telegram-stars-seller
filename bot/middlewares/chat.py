import logging

from telegram import ChatMember, Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from django.conf import settings


logger = logging.getLogger(__name__)


async def enforce_private_chats_only_or_admin_chat(update: object, _: ContextTypes.DEFAULT_TYPE) -> None:
    if not isinstance(update, Update):
        return

    chat = update.effective_chat

    if not chat:
        return

    if chat.type == chat.PRIVATE:
        return

    if update.my_chat_member:
        chat_member = update.my_chat_member.new_chat_member
        status = chat_member.status
        if status in [chat_member.LEFT, chat_member.BANNED]:
            raise ApplicationHandlerStop()

    chat_id = chat.id
    if chat_id != settings.ADMIN_CHAT_ID and chat_id != settings.CHANNEL_ID:  # pyright: ignore[reportAny]
        try:
            logger.info(f"Обнаружен несанкционированный чат {chat.title} ({chat_id}). Попытка выхода...")
            if await chat.leave():
                logger.info("Выход из чата прошёл успешно!")
            else:
                logger.error(f"Не удалось выйти из чата {chat_id} по неизвестной причине (возможно сбой сети)")

        except Exception as exc:
            if "not a member" not in str(exc):
                logger.error(f"Не удалось выйти из чата {chat_id}: {exc}")

    raise ApplicationHandlerStop()
