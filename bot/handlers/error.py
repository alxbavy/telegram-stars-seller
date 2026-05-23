from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.keyboards.error import KeyboardMethodError, build_error_kb

from bot.utils.injector import inject

from bot.context import get_view_context

from core.integrations.fragment import FragmentAPIError
from core.integrations.platega import PlategaAPIError
from core.services.payment import MaintenanceModeException
from core.services.support import SupportService


@inject
async def error_handler(update: object | None, context: ContextTypes.DEFAULT_TYPE, support_service: SupportService) -> None:
    if not isinstance(update, Update):
        raise context.error

    support_url = await support_service.get_support_url()
    parse_mode = ParseMode.HTML

    if isinstance(context.error, FragmentAPIError):
        text = (
            "❌ Произошла ошибка. Можете прочитать текст ошибки, и, если уверены, попробовать снова.\n\n"
            "Также, можно начать новый заказ, или вернуться назад, если есть возможность, или "
            "обратиться в тех. поддержку с текстом ошибки.\n\n"
            f"Текст ошибки:\n<pre>{context.error}</pre>"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, PlategaAPIError):
        text = (
            "❌ Произошла ошибка. Можете прочитать текст ошибки, и, если уверены, попробовать снова.\n\n"
            "Также, можно начать новый заказ, или вернуться назад, если есть возможность, или "
            "обратиться в тех. поддержку с текстом ошибки.\n\n"
            f"Текст ошибки:\n<pre>{context.error}</pre>"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, KeyboardMethodError):
        text = (
            "❌ Произошла ошибка. Метод оплаты недоступен по техническим причинам.\n\n"
            "Можете попробовать выбрать другой метод оплаты, или вернуться назад, или обратиться в тех. поддержку"
            "с текстом ошибки.\n\n"
            f"Текст ошибки:\n<pre>{context.error}</pre>```"
        )
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    elif isinstance(context.error, MaintenanceModeException):
        text = (
            "⚠️ Извините, бот на техническом перерыве...\n\n"
            "(Если вы были в процессе создания заказа, то он был отменён, поэтому вам нужно будет создать новый заказ)"
        )
        ctx = get_view_context(context)
        ctx.active_conversation = None
        _ = await update.effective_user.send_message(text, reply_markup=build_error_kb(support_url), parse_mode=parse_mode)

    raise context.error
