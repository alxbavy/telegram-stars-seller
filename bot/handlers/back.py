from typing import cast

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.start import start_handler

from bot.renderers.order import (
    show_choose_quantity,
    show_custom_quantity_input,
    show_choose_recipient,
    show_enter_username,
    show_payment_methods
)
from bot.renderers.profile import show_profile_page

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import BackCallback, manage_callback_data
from bot.context import clear_profile_data, clear_temporary_messages, get_view_context
from bot.enums import BackDestination
from bot.states import BotConversationState

from core.repositories.utils import db_action_with_tenacity
from core.services.promo_code import PromoCodeService
from core.services.user import UserService
from core.ioc import inject


back_destination_registry: dict[BackDestination, UpdateWithContextHandler[[], BotConversationState]] = {}
register = build_async_handlers_register(back_destination_registry)


@register(BackDestination.MAIN_MENU)
async def handle_destination_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_profile_data(context)
    return await start_handler(update, context)


@register(BackDestination.CHOOSE_QUANTITY)
async def handle_destination_choose_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_choose_quantity(update, context)
    return BotConversationState.CHOOSE_QUANTITY


@register(BackDestination.CUSTOM_QUANTITY_INPUT)
async def handle_destination_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_custom_quantity_input(update, context)
    return BotConversationState.CUSTOM_QUANTITY_INPUT


@register(BackDestination.CHOOSE_RECIPIENT)
async def handle_destination_choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_choose_recipient(update, context)
    return BotConversationState.CHOOSE_RECIPIENT


@register(BackDestination.ENTER_GIFT_USERNAME)
async def handle_destination_enter_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_enter_username(update, context)
    return BotConversationState.ENTER_GIFT_USERNAME


@register(BackDestination.CHOOSE_PAYMENT)
@inject
async def handle_destination_choose_payment(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: FromDishka[PromoCodeService]
):
    ctx = get_view_context(context)
    stars_count = cast(int, ctx.order.quantity)  # noqa
    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id, update.effective_user.id
    )
    _ = await show_payment_methods(update, context, stars_count, active_promo, ctx.order.target_username)
    return BotConversationState.CHOOSE_PAYMENT


@register(BackDestination.PROFILE)
@inject
async def handle_destination_profile(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        user_service: FromDishka[UserService]
):
    ctx = get_view_context(context)
    profile_data = ctx.profile_data
    if profile_data is None:
        profile_data = await db_action_with_tenacity(
            user_service.get_profile_data, update.effective_user.id
        )
    _ = await show_profile_page(update, context, profile_data)
    return BotConversationState.PROFILE


# @register(BackDestination.REFERRALS_LIST)
# async def handle_destination_referrals_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     # Заглушка для возврата к списку рефералов
#     # _ = await show_referrals_list(update, context, referrals_dto)
#     return BotConversationState.REFERRALS_LIST


@ensure_use_active_conversation_with_callback
async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Единый контроллер для обработки всех кнопок 'Назад'.
    Определяет куда вернуться по BackDestination и восстанавливает контекст.
    """

    await clear_temporary_messages(context)

    async with manage_callback_data(update, BackCallback) as cb_data:
        if isinstance(cb_data, int):
            assert cb_data == ConversationHandler.END
            return cb_data

        handler = back_destination_registry[cb_data.destination]
        return await handler(update, context)
