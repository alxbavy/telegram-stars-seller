from telegram.ext import ContextTypes
from telegram import Update

from bot.keyboards.error import build_error_kb
from bot.utils.injector import inject
from core.integrations.fragment import FragmentAPIError
from core.services.support import SupportService


@inject
async def error_handler(update: object | None, context: ContextTypes.DEFAULT_TYPE, support_service: SupportService) -> None:
    if isinstance(context.error, FragmentAPIError) and isinstance(update, Update):
        text = (
            "❌ Произошла ошибка. Можете прочитать текст ошибки, и, если уверены, попробовать снова.\n\n"
            "Также, можно начать новый заказ, или вернуться назад, если есть возможность, или "
            "обратиться в тех. поддержку с текстом ошибки.\n\n"
            f"Текст ошибки:\n```{context.error}```"
        )
        support_url = await support_service.get_support_url()
        _ = await update.effective_message.reply_text(text, reply_markup=build_error_kb(support_url))
        return

    raise context.error
