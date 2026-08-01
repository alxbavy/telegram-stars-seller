from decimal import Decimal
from typing import Literal, cast

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.handlers.back import handle_destination_custom_quantity_input, handle_destination_main_menu

from bot.renderers.order import (
    show_choose_quantity,
    show_choose_recipient,
    show_enter_username,
    show_payment_methods,
    show_order_confirmation
)
from bot.renderers.promo_code import show_enter_promo

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.channel_subscription import is_user_subscribed
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import SubscriptionCallback, manage_callback_data
from bot.context import clear_context, get_view_context
from bot.enums import BackDestination
from bot.states import BotConversationState

from core.repositories.utils import db_action_with_tenacity
from core.services.promo_code import PromoCodeService
from core.ioc import inject


back_destination_registry: dict[BackDestination, UpdateWithContextHandler[[], BotConversationState]] = {}
register = build_async_handlers_register(back_destination_registry)


_ = register(BackDestination.MAIN_MENU)(handle_destination_main_menu)


@register(BackDestination.CHOOSE_QUANTITY)
async def _handle_destination_choose_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_context(context)
    _ = await show_choose_quantity(update, context)
    return BotConversationState.CHOOSE_QUANTITY


_ = register(BackDestination.CUSTOM_QUANTITY_INPUT)(handle_destination_custom_quantity_input)


@register(BackDestination.CHOOSE_RECIPIENT)
async def _handle_destination_choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)

    if ctx.order.quantity is None:
        return await cast(
            UpdateWithContextHandler[[], Literal[BotConversationState.CHOOSE_QUANTITY]], _handle_destination_choose_quantity
        )(update, context)

    _ = await show_choose_recipient(update, context)
    return BotConversationState.CHOOSE_RECIPIENT


@register(BackDestination.ENTER_GIFT_USERNAME)
async def _handle_destination_enter_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)

    if ctx.order.quantity is None:
        return await cast(
            UpdateWithContextHandler[[], Literal[BotConversationState.CHOOSE_QUANTITY]],
            _handle_destination_choose_quantity
        )(update, context)

    _ = await show_enter_username(update, context)
    return BotConversationState.ENTER_GIFT_USERNAME


@register(BackDestination.CHOOSE_PAYMENT)
@inject
async def _handle_destination_choose_payment(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: FromDishka[PromoCodeService]  # noqa
):
    ctx = get_view_context(context)

    if ctx.order.quantity is None:
        return await cast(
            UpdateWithContextHandler[[], Literal[BotConversationState.CHOOSE_QUANTITY]],
            _handle_destination_choose_quantity
        )(update, context)

    stars_count = ctx.order.quantity
    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id, update.effective_user.id
    )
    _ = await show_payment_methods(update, context, stars_count, active_promo, ctx.order.target_username)
    return BotConversationState.CHOOSE_PAYMENT


@register(BackDestination.ENTER_PROMO)
@inject
async def _handle_destination_enter_promo(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: FromDishka[PromoCodeService]  # noqa
):
    ctx = get_view_context(context)

    if ctx.order.quantity is None:
        return await cast(
            UpdateWithContextHandler[[], Literal[BotConversationState.CHOOSE_QUANTITY]],
            _handle_destination_choose_quantity
        )(update, context)

    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id, update.effective_user.id
    )
    _ = await show_enter_promo(update, context, active_promo)
    return BotConversationState.ENTER_PROMO


@register(BackDestination.ORDER_CONFIRMATION)
@inject
async def _handle_destination_order_confirmation(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: FromDishka[PromoCodeService]  # noqa
):
    ctx = get_view_context(context)

    if ctx.order.quantity is None or ctx.order.price is None:
        return await cast(
            UpdateWithContextHandler[[], Literal[BotConversationState.CHOOSE_QUANTITY]],
            _handle_destination_choose_quantity
        )(update, context)

    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id, update.effective_user.id
    )
    _ = await show_order_confirmation(
        update, context,
        ctx.order.quantity, Decimal(ctx.order.price), ctx.order.target_username, active_promo
    )
    return BotConversationState.ORDER_CONFIRMATION


@ensure_use_active_conversation_with_callback
async def handle_i_subscribed_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with manage_callback_data(update, SubscriptionCallback) as cb_data:
        if isinstance(cb_data, int):
            assert cb_data == ConversationHandler.END
            return cb_data

        if not await is_user_subscribed(update, context):
            _ = await update.callback_query.answer(
                text="Ты всё ещё не подписан(-а) — подпишись на канал", show_alert=True
            )
            return BotConversationState.NOT_SUBSCRIBED

        handler = back_destination_registry[cb_data.back_destination]
        return await handler(update, context)
