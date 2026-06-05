import logging
import traceback
import json
import pickle

from telegram import Update
from telegram.ext import ContextTypes, InvalidCallbackData
from telegram.constants import ParseMode

from bot.keyboards.error import KeyboardMethodError, build_error_kb

from bot.utils.injector import inject

from bot.context import get_view_context

from core.integrations.fragment.errors import FragmentAPIError, FragmentAPITemporaryError, FragmentAPITooManyRequests
from core.integrations.platega.schemas import PlategaAPIError
from core.services.payment import MaintenanceModeException
from core.services.support import SupportService


logger = logging.getLogger(__name__)


@inject
async def error_handler(update: object | None, context: ContextTypes.DEFAULT_TYPE, support_service: SupportService) -> None:
    logger.error("Произошло исключение при обработке обновления:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_dict() if isinstance(update, Update) else str(update)

    logger.debug(f"Update: {json.dumps(update_str, ensure_ascii=False, indent=2)}")
    logger.debug(f"Traceback: {tb_string}")

    if not isinstance(update, Update):
        return

    support_url = await support_service.get_support_url()
    parse_mode = ParseMode.HTML
    error_type = context.error.__class__.__name__

    if isinstance(context.error, (FragmentAPIError, PlategaAPIError)):
        text = (
            "❌ <b>Произошла ошибка. Можешь прочитать текст ошибки, и, если уверен, попробовать снова</b>\n\n"
            "Также, можешь начать новый заказ, или вернуться назад, если есть возможность, или "
            "обратиться в тех. поддержку с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

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
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, KeyboardMethodError):
        text = (
            "❌ <b>Произошла ошибка. Метод оплаты недоступен по техническим причинам</b>\n\n"
            "Можешь попробовать выбрать другой метод оплаты, или вернуться назад, или обратиться в тех. поддержку "
            "с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, MaintenanceModeException):
        text = (
            "⚠️ <b>Извини, бот на техническом перерыве...</b>\n\n"
            "Если оформлялся заказ, то он был отменён, поэтому в таком случае нужно начать новый с помощью /start"
        )
        ctx = get_view_context(context)
        try:
            _ = await ctx.active_conversation.delete()
        except:
            pass
        ctx.active_conversation = None
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, InvalidCallbackData) and update.callback_query:
        text = (
            "❌ Не получилось обработать кнопку...\n"
            "Начни заказ снова с помощью /start или обратись в тех. поддержку, если ошибка останется"
        )
        _ = await update.callback_query.answer(text, show_alert=True)

    elif isinstance(context.error, (pickle.UnpicklingError, TypeError, AttributeError)):
        text = (
            "⚠️ <b>Структура меню обновилась</b>\n\n"
            "Начни заказ снова с помощью /start или обратись в тех. поддержку, если ошибка останется"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    else:
        text = (
            "❌ <b>Произошла непредвиденная ошибка!</b>\n\n"
            "Если уверен, можешь попытаться повторить последнее действие, начать новый заказ, или обратиться в тех. "
            "поддержку с текстом ошибки\n\n"
            f"Текст ошибки:\n<pre>{error_type}: {context.error}</pre>"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)
