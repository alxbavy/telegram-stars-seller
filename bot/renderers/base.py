import logging
from io import BufferedReader
from pathlib import Path
from urllib.parse import urlencode
from contextlib import contextmanager
from typing import cast, TypedDict
from collections.abc import Generator

from httpx import NetworkError

from telegram import InlineKeyboardMarkup, Update, InputMediaPhoto, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter

from django.conf import settings

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from bot.utils.retries import sleep_for_retry_after


logger = logging.getLogger(__name__)


class _MessageActionKwargs(TypedDict):
    reply_markup: InlineKeyboardMarkup | None
    parse_mode: ParseMode


class _MessageEditMediaKwargs(TypedDict):
    media: InputMediaPhoto
    reply_markup: InlineKeyboardMarkup | None


class _MessageEditTextKwargs(TypedDict):
    text: str
    reply_markup: InlineKeyboardMarkup | None
    parse_mode: ParseMode


@contextmanager
def create_media_source(photo_name: str) -> Generator[BufferedReader | str]:
    image_path = cast(Path, settings.BASE_DIR / "images" / photo_name)
    query = {"text": str(photo_name)}

    media_source: BufferedReader | str = (
        open(image_path, "rb") if image_path.exists()
        else f"https://dummyimage.com/600x400/000/fff&{urlencode(query)}"
    )
    try:
        yield media_source

    finally:
        if isinstance(media_source, BufferedReader):
            media_source.close()


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential_jitter(initial=1.0, max=4.0, jitter=1.0),
    retry=retry_if_exception_type((NetworkError, RetryAfter)),
    before_sleep=sleep_for_retry_after,
    reraise=True
)
async def update_existing_message(
        update_or_msg: Update | Message,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
        photo_name: str | None
) -> Message | None:
    """
    Возвращает либо изменённое сообщение, либо `None` в случае неудачи.

    Неудача будет в случае любого `BadRequest` кроме того с "not modified", либо если `update_or_msg` является `Update`
    с `callback_query` равным `None`.
    """

    if isinstance(update_or_msg, Update) and update_or_msg.callback_query is None:
        return None

    parse_mode = ParseMode.HTML
    try:
        if photo_name:
            with create_media_source(photo_name) as media_source:
                media_kwargs: _MessageEditMediaKwargs = {
                    "media": InputMediaPhoto(media=media_source, caption=text, parse_mode=parse_mode),
                    "reply_markup":  reply_markup
                }

                if isinstance(update_or_msg, Update):
                    return cast(Message, await update_or_msg.callback_query.edit_message_media(**media_kwargs))  # noqa
                else:
                    return cast(Message, await update_or_msg.edit_media(**media_kwargs))  # noqa

        text_kwargs: _MessageEditTextKwargs = {
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode
        }
        if isinstance(update_or_msg, Update):
            return cast(Message, await update_or_msg.callback_query.edit_message_text(**text_kwargs))  # noqa
        else:
            return cast(Message, await update_or_msg.edit_text(**text_kwargs))  # noqa

    except BadRequest as exc:
        err_msg = str(exc)
        if "not modified" in err_msg.lower():
            if isinstance(update_or_msg, Update):
                return cast(Message, update_or_msg.effective_message)  # noqa
            else:
                return update_or_msg
        logger.exception(f"{exc.__class__.__name__} - {str(exc)}")
        return None

    except (RetryAfter, NetworkError) as exc:
        raise exc


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential_jitter(initial=1.0, max=4.0, jitter=1.0),
    retry=retry_if_exception_type((NetworkError, RetryAfter)),
    before_sleep=sleep_for_retry_after,
    reraise=True
)
async def send_new_message(
        update: Update,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
        photo_name: str | None
) -> Message:
    kwargs: _MessageActionKwargs = {"reply_markup": reply_markup, "parse_mode": ParseMode.HTML}

    if photo_name:
        with create_media_source(photo_name) as media_source:
            return await update.effective_user.send_photo(photo=media_source, caption=text, **kwargs)

    return await update.effective_user.send_message(text=text, **kwargs)


async def render_screen(
        update: Update,
        text: str,
        reply_markup: InlineKeyboardMarkup | None,
        photo_name: str | None = None
) -> Message:
    """
    Эта функция должна использоваться только в личном чате. Если её использовать для обработки Inline сообщений, то
    поведение не гарантированно, и скорее всего возникнет ошибка.
    """

    if update.callback_query is not None:
        _ = await update.callback_query.answer()
        msg = await update_existing_message(update, text, reply_markup, photo_name)
        if isinstance(msg, Message):
            return msg

    _ = await delete_message(update.effective_message)

    return await send_new_message(update, text, reply_markup, photo_name)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential_jitter(initial=1.0, max=4.0, jitter=1.0),
    retry=retry_if_exception_type((NetworkError, RetryAfter)),
    before_sleep=sleep_for_retry_after,
    reraise=True
)
async def delete_message(msg: Message | None) -> bool:
    if msg is None:
        return True

    try:
        return await msg.delete()

    except BadRequest:
        return True
