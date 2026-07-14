import logging
import traceback
import json
import pickle
from dataclasses import is_dataclass, asdict
from decimal import Decimal
from typing import override, overload

from httpx import ConnectError

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes, InvalidCallbackData

from bot.keyboards.error import KeyboardMethodError, build_error_kb
from bot.renderers.base import delete_message, send_new_message
from bot.context import get_view_context

from core.integrations.fragment.errors import FragmentAPIError, FragmentAPITemporaryError, FragmentAPITooManyRequests
from core.integrations.platega.errors import PlategaAPIError
from core.services.payment import MaintenanceModeException, NoUsernameError
from core.services.support import SupportService
from core.ioc import inject


logger = logging.getLogger(__name__)


class DataclassEncoder(json.JSONEncoder):
    @override
    def default(self, o: object):
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)  # noqa
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)  # pyright: ignore[reportAny]


@overload
async def error_handler(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: object | None, context: ContextTypes.DEFAULT_TYPE
) -> None: ...


@inject
async def error_handler(
        update: object | None, context: ContextTypes.DEFAULT_TYPE,
        *,
        support_service: FromDishka[SupportService]
) -> None:
    logger.error("Произошло исключение при обработке обновления:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    logger.debug(f"Update: {json.dumps(update_str, cls=DataclassEncoder, ensure_ascii=False, indent=2)}")
    logger.debug(f"Traceback: {tb_string}")

    if not isinstance(update, Update):
        return

    support_url = await support_service.get_support_url()
    reply_markup = build_error_kb(support_url)
    error_type = context.error.__class__.__name__

    if isinstance(context.error, (FragmentAPIError, PlategaAPIError)):
        text = (
            "❌ <b>Произошла ошибка!</b>\n\n"
            "Попробуй последнее действие снова или вернись назад, если есть возможность. Либо начинай новый заказ "
            "с помощью /start или обратись в тех. поддержку с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )

    elif isinstance(context.error, FragmentAPITooManyRequests):
        retry_after = str(context.error.retry_after) if context.error.retry_after else ""
        text = (
            f"⚠️ <b>Fragment перегружен...</b>\n\n"
            f"{
            'Попробуй последнее действие снова через ' + retry_after + ' секунд или обратись в тех. поддержку' if retry_after
            else 'Обратись в тех. поддержку'
            }"
            f" с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )

    elif isinstance(context.error, FragmentAPITemporaryError):
        text = f"⚠️ <b>Временные неполадки...</b>\n\n{context.error.bot_message}"

    elif isinstance(context.error, NoUsernameError):
        text = (
            f"⚠️ <b>Не получилось определить username...</b>\n\n"
            f"Для перевода звёзд он обязателен, поэтому попробуй сделать заказ заново"
        )

    elif isinstance(context.error, KeyboardMethodError):
        text = (
            "❌ <b>Произошла ошибка!</b>\n\n"
            "Метод оплаты недоступен по техническим причинам. Попробуй другой метод оплаты или вернись назад. Либо "
            "обратись в тех. поддержку с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )

    elif isinstance(context.error, MaintenanceModeException):
        text = (
            "⚠️ <b>Извини, бот на техническом перерыве...</b>\n\n"
            "Если оформлялся заказ, то он был отменён, поэтому в таком случае нужно начать новый с помощью /start"
        )

        ctx = get_view_context(context)
        try:
            _ = await delete_message(ctx.active_conversation)
        except Exception:  # noqa
            pass
        ctx.active_conversation = None

    elif isinstance(context.error, InvalidCallbackData) and update.callback_query:
        text = (
            "❌ Не получилось обработать кнопку...\n"
            "Начни заказ снова с помощью /start или обратись в тех. поддержку, если ошибка останется"
        )
        _ = await update.callback_query.answer(text, show_alert=True)
        return

    elif isinstance(context.error, (pickle.UnpicklingError, TypeError, AttributeError)):
        text = (
            "⚠️ <b>Структура меню обновилась...</b>\n\n"
            "Начни заказ снова с помощью /start или обратись в тех. поддержку, если ошибка останется"
        )

    elif isinstance(context.error, ConnectError):
        text = (
            "⚠️ <b>Что-то произошло с соединением...</b>\n\n"
            "Можешь повторить последнее действие\n\n"
            "Либо начни новый заказ — /start\n"
            "Если ошибка останется, обратись в тех. поддержку"
        )

    else:
        text = (
            "❌ <b>Произошла непредвиденная ошибка!</b>\n\n"
            "Попробуй повторить последнее действие, либо начни новый заказ с помощью /start, либо обратись в "
            "тех. поддержку с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )

    _ = await send_new_message(update, text, reply_markup, photo_name=None)
