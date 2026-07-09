import re
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from math import ceil
from typing import cast

from telegram import Update, Message
from telegram.ext import ContextTypes

from bot.keyboards.error import KeyboardMethodError
from bot.renderers.base import delete_message
from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject

from bot.handlers.start import running_users

from bot.renderers.main import send_empty_username_alert
from bot.renderers.order import (
    show_choose_recipient,
    show_custom_quantity_input,
    edit_order_creating_failed_message,
    show_pay_url_not_provided,
    show_payment_methods_dynamic,
    show_large_order_warning,
    show_enter_username,
    show_searching_username,
    show_user_not_found,
    show_order_confirmation, edit_order_created_message, edit_order_creating_message
)

from bot.callbacks import PaymentMethodCallback, RecipientModeCallback, cast_callback, FixedQuantityCallback
from bot.context import get_view_context
from bot.enums import RecipientMode
from bot.states import BotConversationState
from core.integrations.fragment.client import FragmentClient

from core.integrations.utils import retries_with_tenacity
from core.repositories.utils import db_action_with_tenacity
from core.services.payment import PaymentService
from core.services.promo_code import PromoCodeService
from core.services.support import SupportService
from core.services.transaction import TransactionService
from core.services.user import UserService


logger = logging.getLogger(__name__)


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
        # Нужно указывать пустым, так как сюда можно вернуться с предыдущих шагов, где он мог быть заполнен
        ctx.order.target_username = ""

        # noinspection PyUnnecessaryCast
        stars_count = cast(int, ctx.order.quantity)
        _ = await show_payment_methods_dynamic(update, context, stars_count, username=ctx.order.target_username)
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

        _ = await delete_message(ctx.active_conversation)
        msg_searching = await show_searching_username(update, context, username)

        is_found = await retries_with_tenacity(
            fragment_client.resolve_username(username, timeout=30.0, connect=10.0)
        )

        _ = await delete_message(msg_searching)

        if not is_found:
            _ = await show_user_not_found(update, context, username)
            return BotConversationState.ENTER_GIFT_USERNAME

        ctx.order.target_username = username

        # noinspection PyUnnecessaryCast
        stars_count = cast(int, ctx.order.quantity)
        _ = await show_payment_methods_dynamic(update, context, stars_count, username=username)
        return BotConversationState.CHOOSE_PAYMENT_GIFT

    finally:
        running_users.discard(user_id)


# Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен
async def handle_gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_gift_username_helper(update, context)


@inject
async def _handle_payment_method_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        promo_service: PromoCodeService
):
    ctx = get_view_context(context)
    cb_data = cast_callback(PaymentMethodCallback, update.callback_query.data)

    stars = ctx.order.quantity
    price = cb_data.price
    is_gift = ctx.order.recipient_mode == RecipientMode.GIFT

    ctx.order.price = str(price)
    ctx.order.payment_method = cb_data.method
    ctx.order.payment_external_id = cb_data.method_external_id
    ctx.order.payment_api = cb_data.method_api

    if stars is None:
        raise AttributeError("order stars amount is None")

    if price is None:
        raise NotImplementedError("needs static implementation")

    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id(update.effective_user.id)
    )

    _ = await show_order_confirmation(
        update, context,
        stars, price, is_gift, ctx.order.target_username, active_promo
    )
    return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF


@ensure_use_active_conversation_with_callback
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_payment_method_helper(update, context)


@inject
async def _handle_order_confirmed_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        fragment_client: FragmentClient, payment_service: PaymentService,
        transaction_service: TransactionService, promo_service: PromoCodeService,
        user_service: UserService, support_service: SupportService
):
    ctx = get_view_context(context)

    is_gift = ctx.order.recipient_mode == RecipientMode.GIFT

    if not is_gift and update.effective_user.username is None:
        _ = await send_empty_username_alert(update)
        return BotConversationState.ORDER_CONFIRMATION_SELF

    # Если maintenance_mode, выбросится исключение для обработки в error_handler
    await db_action_with_tenacity(payment_service.ensure_no_maintenance_mode())

    amount_stars = ctx.order.quantity
    price = ctx.order.price
    method_id = ctx.order.payment_external_id
    method_api = ctx.order.payment_api

    if amount_stars is None:
        raise AttributeError("amount_stars is None во время создания заказа")
    if price is None:
        raise AttributeError("price is None во время создания заказа")
    if method_id is None:
        raise AttributeError("method_id is None во время создания заказа")
    if method_api is None:
        raise AttributeError("method_api is None во время создания заказа")

    # TODO: сделать механизм удержания баланса
    # Если не получится определить, хватает ли средств для перевода звёзд, выбросится исключение для обработки в error_handler
    await retries_with_tenacity(
        fragment_client.check_is_enough_currency_for_stars(amount_stars, timeout=30.0, connect=10.0)
    )

    try:
        price = Decimal(price)
    except ValueError:
        raise KeyboardMethodError("Цена должна быть в формате Decimal")

    try:
        method_id = int(method_id)
    except ValueError:
        raise KeyboardMethodError("Внешний ID метода оплаты должен быть целым числом для используемого API")

    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id(update.effective_user.id)
    )

    order_msg = update.effective_message
    if order_msg is None:
        raise RuntimeError("По какой-то причине сообщение заказа отсутствует при создании заказа")

    payment_dto, parsed_payload = await db_action_with_tenacity(payment_service.create_payment(
        user_id=update.effective_user.id,
        message_id=order_msg.message_id,
        price=price,
        stars_count=amount_stars,
        payment_api=method_api,
        method=method_id,
        target_username=ctx.order.target_username,
        promo=active_promo
    ))

    pay_url = payment_dto.pay_url
    if pay_url is None:
        _ = await show_pay_url_not_provided(update, context, await support_service.get_support_url())
        return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF

    parsed_payload["pay_url"] = pay_url

    _ = await db_action_with_tenacity(transaction_service.create_transaction(
        payment_dto.transaction_id,
        parsed_payload,
        payment_method=f"{method_api} - {method_id}",
        expires_in=payment_dto.expires_in
    ))

    ctx.order.checkout_transaction_id = str(payment_dto.transaction_id)
    ctx.order.checkout_url = payment_dto.pay_url

    actual_expires_in = datetime.strptime(payment_dto.expires_in, "%H:%M:%S")
    expires_in_td = timedelta(hours=actual_expires_in.hour, minutes=actual_expires_in.minute,
                              seconds=actual_expires_in.second)
    expires_in_minutes = str(ceil(expires_in_td.total_seconds() / 60))

    msg = await edit_order_creating_message(order_msg, is_gift)
    if msg is None:
        raise RuntimeError(f"Не получилось изменить сообщение с id {order_msg.message_id}")

    db_action = await db_action_with_tenacity(
        transaction_service.save_message_id(payment_dto.transaction_id, msg.message_id), suppress_exc=True
    )
    if db_action is None:
        is_changed_successfully = False
    else:
        is_changed_successfully, _ = db_action

    if is_changed_successfully:
        msg = await edit_order_created_message(
            msg,
            amount_stars, payment_dto.price, pay_url, payment_dto.transaction_id,
            expires_in_minutes, is_gift, ctx.order.target_username, active_promo
        )
        if msg is None:
            raise RuntimeError(f"Не получилось изменить сообщение с id {order_msg.message_id}")

        _ = await db_action_with_tenacity(
            user_service.update_active_promo(update.effective_user.id, None)
        )

        return BotConversationState.ORDER_CONFIRMED

    else:
        msg = await edit_order_creating_failed_message(msg, is_gift)
        err_msg = (
            f"При попытке сохранить id сообщения заказа или транзакция {payment_dto.transaction_id} не была найдена, "
            f"или произошла непредвиденная ошибка"
        )
        if msg is None:
            err_msg += f". Также не получилось обновить сообщения заказа с id {order_msg.message_id}"
        logger.exception(err_msg)
        return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF


@ensure_use_active_conversation_with_callback
async def handle_order_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_order_confirmed_helper(update, context)
