import asyncio
import logging
from mimetypes import guess_type
from io import BufferedReader
from typing import TypedDict, NotRequired

from django.conf import settings
from django.db.models import QuerySet

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from tenacity import retry

from core.domain.tenacity_utils import TelegramRetryConfig
from core.domain.type_aliases import AsyncCallable
from core.models import Broadcast, TelegramUser


logger = logging.getLogger(__name__)

_parse_mode = ParseMode.HTML

_retry_config = TelegramRetryConfig().asdict


class _PhotoKwargs(TypedDict):
    chat_id: int
    parse_mode: ParseMode
    photo: str | BufferedReader
    caption: str
    reply_markup: InlineKeyboardMarkup | None
    message_thread_id: NotRequired[int | None]


class _VideoKwargs(TypedDict):
    chat_id: int
    parse_mode: ParseMode
    video: str | BufferedReader
    caption: str
    reply_markup: InlineKeyboardMarkup | None
    message_thread_id: NotRequired[int | None]


class _DocumentKwargs(TypedDict):
    chat_id: int
    parse_mode: ParseMode
    document: str | BufferedReader
    caption: str
    reply_markup: InlineKeyboardMarkup | None
    message_thread_id: NotRequired[int | None]


class _TextKwargs(TypedDict):
    chat_id: int
    parse_mode: ParseMode
    text: str
    reply_markup: InlineKeyboardMarkup | None
    message_thread_id: NotRequired[int | None]


class _BroadcastResult(TypedDict):
    success: int
    failed: int


@retry(**_retry_config)
async def _retry_action[R](
        bot_action: AsyncCallable[..., R],
        kwargs: _PhotoKwargs | _VideoKwargs | _DocumentKwargs | _TextKwargs
) -> R:
    return await bot_action(**kwargs)


def _build_keyboard(
        button_texts: list[list[str]] | None,
        button_urls: list[list[str]] | None
) -> InlineKeyboardMarkup | None:
    if not button_texts or not button_urls:
        return None

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=t, url=u) for t, u in zip(texts, urls)]
        for texts, urls in zip(button_texts, button_urls)
    ])


async def _send_preview_and_get_file_id(
        bot: Bot,
        chat_id: int,
        text: str,
        media_path: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None,
        thread_id: int | None = None
) -> str | None:
    if not media_path:
        text_kwargs = _TextKwargs(
            chat_id=chat_id, parse_mode=_parse_mode,
            text=text, reply_markup=reply_markup, message_thread_id=thread_id
        )
        _ = await _retry_action(bot.send_message, text_kwargs)
        return None

    mime_type, _ = guess_type(media_path)
    with open(media_path, "rb") as f:
        if mime_type and mime_type.startswith("image"):
            photo_kwargs = _PhotoKwargs(
                chat_id=chat_id, parse_mode=_parse_mode,
                photo=f, caption=text, reply_markup=reply_markup, message_thread_id=thread_id
            )
            msg = await _retry_action(bot.send_photo, photo_kwargs)
            return msg.photo[-1].file_id

        elif mime_type and mime_type.startswith("video"):
            video_kwargs = _VideoKwargs(
                chat_id=chat_id, parse_mode=_parse_mode,
                video=f, caption=text, reply_markup=reply_markup, message_thread_id=thread_id
            )
            msg = await _retry_action(bot.send_video, video_kwargs)
            return msg.video.file_id

        else:
            document_kwargs = _DocumentKwargs(
                chat_id=chat_id, parse_mode=_parse_mode,
                document=f, caption=text, reply_markup=reply_markup, message_thread_id=thread_id
            )
            msg = await _retry_action(bot.send_document, document_kwargs)
            return msg.document.file_id


async def process_preview(bot: Bot, broadcast_id: int) -> str:
    broadcast = await Broadcast.objects.aget(id=broadcast_id)

    broadcast_name = f'"{broadcast.name}"'
    if not broadcast_name:
        broadcast_name = broadcast_id

    reply_markup = _build_keyboard(broadcast.button_texts, broadcast.button_urls)
    media_path = broadcast.media.path if broadcast.media else None

    try:
        file_id = await _send_preview_and_get_file_id(
            bot=bot,
            chat_id=settings.ADMIN_CHAT_ID,  # pyright: ignore[reportAny]
            text=broadcast.text,
            media_path=media_path,
            reply_markup=reply_markup,
            thread_id=settings.ADMIN_BROADCAST_TOPIC_ID  # pyright: ignore[reportAny]
        )

        broadcast.telegram_file_id = file_id
        broadcast.preview_sent = True

        await broadcast.asave(update_fields=['telegram_file_id', 'preview_sent'])

        return f"broadcast {broadcast_name} preview send success"

    except Exception as exc:
        logger.exception(f"Ошибка отправки предпросмотра рассылки {broadcast_name}: {exc}", exc_info=False)
        return f"broadcast {broadcast_name} preview send fail"


async def _mass_send_photo(
        bot: Bot, broadcast_name: str | int,
        users_qs: QuerySet[TelegramUser],
        file_id: str, text: str, reply_markup: InlineKeyboardMarkup | None
) -> _BroadcastResult:
    success = 0
    failed = 0

    async for user in users_qs:
        try:
            photo_kwargs = _PhotoKwargs(
                chat_id=user.telegram_id, parse_mode=_parse_mode,
                photo=file_id, caption=text, reply_markup=reply_markup
            )
            _ = await _retry_action(bot.send_photo, photo_kwargs)
            success += 1
            await asyncio.sleep(0.05)

        except Exception as exc:
            logger.exception(
                f"Не удалось отправить {broadcast_name} юзеру {user.telegram_id}: {exc}", exc_info=False
            )
            failed += 1

    return _BroadcastResult(success=success, failed=failed)


async def _mass_send_video(
        bot: Bot, broadcast_name: str | int,
        users_qs: QuerySet[TelegramUser],
        file_id: str, text: str, reply_markup: InlineKeyboardMarkup | None
) -> _BroadcastResult:
    success = 0
    failed = 0

    async for user in users_qs:
        try:
            video_kwargs = _VideoKwargs(
                chat_id=user.telegram_id, parse_mode=_parse_mode,
                video=file_id, caption=text, reply_markup=reply_markup
            )
            _ = await _retry_action(bot.send_video, video_kwargs)
            success += 1
            await asyncio.sleep(0.05)

        except Exception as exc:
            logger.exception(
                f"Не удалось отправить {broadcast_name} юзеру {user.telegram_id}: {exc}", exc_info=False
            )
            failed += 1

    return _BroadcastResult(success=success, failed=failed)


async def _mass_send_document(
        bot: Bot, broadcast_name: str | int,
        users_qs: QuerySet[TelegramUser],
        file_id: str, text: str, reply_markup: InlineKeyboardMarkup | None
) -> _BroadcastResult:
    success = 0
    failed = 0

    async for user in users_qs:
        try:
            document_kwargs = _DocumentKwargs(
                chat_id=user.telegram_id, parse_mode=_parse_mode,
                document=file_id, caption=text, reply_markup=reply_markup
            )
            _ = await _retry_action(bot.send_document, document_kwargs)
            success += 1
            await asyncio.sleep(0.05)

        except Exception as exc:
            logger.exception(
                f"Не удалось отправить {broadcast_name} юзеру {user.telegram_id}: {exc}", exc_info=False
            )
            failed += 1

    return _BroadcastResult(success=success, failed=failed)


async def _mass_send_text(
        bot: Bot, broadcast_name: str | int,
        users_qs: QuerySet[TelegramUser],
        text: str, reply_markup: InlineKeyboardMarkup | None
) -> _BroadcastResult:
    success = 0
    failed = 0

    async for user in users_qs:
        try:
            text_kwargs = _TextKwargs(
                chat_id=user.telegram_id, parse_mode=_parse_mode,
                text=text, reply_markup=reply_markup
            )
            _ = await _retry_action(bot.send_message, text_kwargs)
            success += 1
            await asyncio.sleep(0.05)

        except Exception as exc:
            logger.exception(
                f"Не удалось отправить {broadcast_name} юзеру {user.telegram_id}: {exc}", exc_info=False
            )
            failed += 1

    return _BroadcastResult(success=success, failed=failed)


async def _mass_send(
        bot: Bot, broadcast_name: str | int,
        users_qs: QuerySet[TelegramUser],
        text: str,
        file_id: str | None = None,
        media_path: str | None = None,
        reply_markup: InlineKeyboardMarkup | None = None
) -> _BroadcastResult:
    if file_id and media_path:
        mime_type, _ = guess_type(media_path)

        if mime_type and mime_type.startswith('image'):
            return await _mass_send_photo(bot, broadcast_name, users_qs, file_id, text, reply_markup)

        elif mime_type and mime_type.startswith('video'):
            return await _mass_send_video(bot, broadcast_name, users_qs, file_id, text, reply_markup)

        else:
            return await _mass_send_document(bot, broadcast_name, users_qs, file_id, text, reply_markup)

    return await _mass_send_text(bot, broadcast_name, users_qs, text, reply_markup)


async def process_broadcast(bot: Bot, broadcast_id: int) -> str:
    broadcast = await Broadcast.objects.aget(id=broadcast_id)

    broadcast_name = f'"{broadcast.name}"'
    if not broadcast_name:
        broadcast_name = broadcast_id

    reply_markup = _build_keyboard(broadcast.button_texts, broadcast.button_urls)
    media_path = broadcast.media.path if broadcast.media else None

    users_qs = TelegramUser.objects.all()

    broadcast_result = await _mass_send(
        bot=bot, broadcast_name=broadcast_name,
        users_qs=users_qs,
        text=broadcast.text,
        file_id=broadcast.telegram_file_id,
        media_path=media_path,
        reply_markup=reply_markup
    )

    broadcast.is_sent = True
    await broadcast.asave(update_fields=['is_sent'])

    return f"mass broadcast {broadcast_name} -> {broadcast_result}"
