import re
from typing import cast
from datetime import datetime, timedelta
from math import ceil

from telegram import Update, Message
from telegram.ext import ContextTypes

from bot.keyboards.error import KeyboardMethodError
from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject

from bot.handlers.start import running_users

from bot.renderers.main import send_empty_username_alert
from bot.renderers.order import (
    show_choose_recipient,
    show_custom_quantity_input,
    show_payment_methods_dynamic,
    show_large_order_warning,
    show_enter_username,
    show_searching_username,
    show_user_not_found,
    show_order_confirmation
)

from bot.callbacks import PaymentMethodCallback, RecipientModeCallback, cast_callback, FixedQuantityCallback
from bot.cleanup import clear_specific_transaction
from bot.context import get_view_context
from bot.enums import RecipientMode
from bot.states import BotConversationState
from core.integrations.fragment.client import FragmentClient

from core.services.payment import PaymentService
from core.services.support import SupportService


@ensure_use_active_conversation_with_callback
async def handle_fixed_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data = cast_callback(FixedQuantityCallback, update.callback_query.data)
    ctx = get_view_context(context)
    ctx.order.quantity = cb_data.amount

    _ = await show_choose_recipient(update, context)
    return BotConversationState.CHOOSE_RECIPIENT


@ensure_use_active_conversation_with_callback
async def handle_custom_quantity_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_custom_quantity_input(update, context)
    return BotConversationState.CUSTOM_QUANTITY_INPUT


@inject
async def _handle_custom_quantity_input_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        support_service: SupportService
):
    user_id = update.effective_user.id
    if user_id in running_users:
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    running_users.add(user_id)

    try:
        # noinspection PyUnnecessaryCast
        user_msg = cast(Message, update.message)

        text = user_msg.text
        if text is None or not text.isdigit():
            return BotConversationState.CUSTOM_QUANTITY_INPUT

        amount = int(text)

        if amount < 50:
            return BotConversationState.CUSTOM_QUANTITY_INPUT

        if amount > 10000:  # Условный лимит
            url = await support_service.get_support_url()
            _ = await show_large_order_warning(update, context, amount, url)
            return BotConversationState.LARGE_ORDER_WARNING

        ctx = get_view_context(context)
        ctx.order.quantity = amount

        _ = await show_choose_recipient(update, context)
        return BotConversationState.CHOOSE_RECIPIENT

    finally:
        running_users.discard(user_id)


# Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен
async def handle_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_custom_quantity_input_helper(update, context)


async def _handle_recipient_mode_helper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data = cast_callback(RecipientModeCallback, update.callback_query.data)
    ctx = get_view_context(context)

    ctx.order.recipient_mode = cb_data.mode
    if cb_data.mode == RecipientMode.SELF:

        if update.effective_user.username is None:
            _ = await send_empty_username_alert(update)
            return BotConversationState.CHOOSE_RECIPIENT

        ctx.order.target_username = ""

        # noinspection PyUnnecessaryCast
        stars_count = cast(int, ctx.order.quantity)
        _ = await show_payment_methods_dynamic(update, context, stars_count, is_gift=False)
        return BotConversationState.CHOOSE_PAYMENT_SELF

    else:
        _ = await show_enter_username(update, context)
        return BotConversationState.ENTER_GIFT_USERNAME


@ensure_use_active_conversation_with_callback
async def handle_recipient_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_recipient_mode_helper(update, context)


@inject
async def _handle_gift_username_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        fragment_client: FragmentClient
):
    user_id = update.effective_user.id
    if user_id in running_users:
        return BotConversationState.ENTER_GIFT_USERNAME

    running_users.add(user_id)

    try:
        user_msg = update.message

        # noinspection PyUnnecessaryCast
        username = cast(str, user_msg.text)
        username_pattern = re.compile(r"^@?[a-zA-Z][a-zA-Z0-9_]{2,31}$")
        if not username_pattern.search(username):
            return BotConversationState.ENTER_GIFT_USERNAME

        ctx = get_view_context(context)

        _ = await ctx.active_conversation.delete()
        msg_searching = await show_searching_username(update, context, username)

        is_found = await fragment_client.resolve_username(username)

        _ = await msg_searching.delete()

        if not is_found:
            _ = await show_user_not_found(update, context, username)
            return BotConversationState.ENTER_GIFT_USERNAME

        ctx.order.target_username = username

        # noinspection PyUnnecessaryCast
        stars_count = cast(int, ctx.order.quantity)
        _ = await show_payment_methods_dynamic(update, context, stars_count, is_gift=True, username=username)
        return BotConversationState.CHOOSE_PAYMENT_GIFT

    finally:
        running_users.discard(user_id)


# Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен
async def handle_gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_gift_username_helper(update, context)


@inject
async def _handle_payment_method_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        fragment_client: FragmentClient, payment_service: PaymentService
):
    # Если maintenance_mode, выбросится исключение для обработки в error_handler
    await payment_service.ensure_no_maintenance_mode()

    cb_data = cast_callback(PaymentMethodCallback, update.callback_query.data)
    ctx = get_view_context(context)

    ctx.order.payment_method = cb_data.method

    # noinspection PyUnnecessaryCast
    amount_stars = cast(int, ctx.order.quantity)
    # Если не получится определить, хватает ли средств для перевода звёзд, выбросится исключение для обработки в error_handler
    await fragment_client.check_is_enough_currency_for_stars(amount_stars)

    if cb_data.price is None:
        raise NotImplementedError("needs static implementation")

    try:
        method_id = int(cb_data.method_external_id)
    except ValueError:
        raise KeyboardMethodError("Внешний ID метода оплаты должен быть целым числом для используемого API")

    payment_dto = await payment_service.create_payment_and_transaction(
        user_id=update.effective_user.id,
        message_id=update.effective_message.message_id,
        price=cb_data.price,
        stars_count=amount_stars,
        payment_api=cb_data.method_api,
        method=method_id,
        target_username=ctx.order.target_username
    )

    ctx.order.checkout_transaction_id = str(payment_dto.transaction_id)
    ctx.order.checkout_url = payment_dto.pay_url

    is_gift = ctx.order.recipient_mode == RecipientMode.GIFT

    actual_expires_in = datetime.strptime(payment_dto.expires_in, "%H:%M:%S")
    expires_in_for_job = actual_expires_in + timedelta(minutes=1)
    delay = timedelta(hours=expires_in_for_job.hour, minutes=expires_in_for_job.minute, seconds=expires_in_for_job.second)
    expires_in_str_for_job = f"{expires_in_for_job.hour:02}:{expires_in_for_job.minute:02}:{expires_in_for_job.second:02}"
    _ = context.job_queue.run_once(
        clear_specific_transaction,
        when = delay,
        data = (payment_dto.transaction_id, expires_in_str_for_job)
    )

    expires_in_td = timedelta(hours=actual_expires_in.hour, minutes=actual_expires_in.minute, seconds=actual_expires_in.second)
    expires_in_minutes = str(ceil(expires_in_td.total_seconds() / 60))
    msg = await show_order_confirmation(
        update, context,
        amount_stars, payment_dto.price, payment_dto.pay_url, payment_dto.transaction_id, expires_in_minutes,
        is_gift, ctx.order.target_username
    )

    print(f"{msg.message_id = }")  # TODO: для дебага вебхука

    return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF


@ensure_use_active_conversation_with_callback
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_payment_method_helper(update, context)
