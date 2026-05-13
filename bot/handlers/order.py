from typing import cast

from telegram import Update, Message
from telegram.ext import ContextTypes

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject

from bot.renderers.order import (
    show_choose_recipient,
    show_custom_quantity_input,
    show_large_order_warning,
    show_payment_methods,
    show_enter_username,
    show_user_not_found,
    show_order_confirmation
)

from bot.callbacks import PaymentMethodCallback, RecipientModeCallback, cast_callback, FixedQuantityCallback
from bot.context import add_temporary_message, clear_temporary_messages, get_view_context
from bot.enums import RecipientMode
from bot.states import BotConversationState

from core.services.payment import PaymentService
from core.services.star_price import StarService
from core.services.support import SupportService
from core.services.telegram import TelegramService


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
    # noinspection PyUnnecessaryCast
    user_msg = cast(Message, update.message)
    text = user_msg.text
    add_temporary_message(context, user_msg)
    if text is None or not text.isdigit():
        temp_msg = await update.message.reply_text("Пожалуйста, введите целое число.")
        add_temporary_message(context, temp_msg)
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    amount = int(text)

    if amount < 50:
        temp_msg = await update.message.reply_text("Пожалуйста, введите целое число больше 50-ти.")
        add_temporary_message(context, temp_msg)
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    await clear_temporary_messages(context)
    ctx = get_view_context(context)
    _ = await ctx.active_conversation.delete()

    if amount > 10000:  # Условный лимит
        url = await support_service.get_support_url()
        _ = await show_large_order_warning(update, context, amount, url)
        return BotConversationState.LARGE_ORDER_WARNING
    ctx.order.quantity = amount

    _ = await show_choose_recipient(update, context)
    return BotConversationState.CHOOSE_RECIPIENT


async def handle_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен."""
    return await _handle_custom_quantity_input_helper(update, context)


@inject
async def _handle_recipient_mode_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        star_service: StarService
):
    cb_data = cast_callback(RecipientModeCallback, update.callback_query.data)
    ctx = get_view_context(context)

    ctx.order.recipient_mode = cb_data.mode
    if cb_data.mode == RecipientMode.SELF:
        ctx.order.target_username = None
        # noinspection PyUnnecessaryCast
        stars_count = cast(int, ctx.order.quantity)
        sbp_price = await star_service.get_order_price(stars_count, "sbp")
        card_price = await star_service.get_order_price(stars_count, "card")
        _ = await show_payment_methods(update, context, sbp_price, card_price, is_gift=False)
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
        tg_api: TelegramService, star_service: StarService
):
    # noinspection PyUnnecessaryCast
    username = cast(str, update.message.text)
    _ = await update.message.delete()

    ctx = get_view_context(context)
    # Транзиентный статус 8a

    _ = await ctx.active_conversation.delete()

    msg = await update.message.reply_text(f"🔎 Ищем пользователя {username}...\n\nЭто займёт пару секунд.")

    # TODO: может быть такое, что при попытке поиска телеграм заставит подождать клиент telethon, прежде чем
    #       можно будет проверить пользователя -> в таком случае пользователю надо бы вывести сообщение, что
    #       нужно подождать Х времени -> получается, .resolve_username(...) помимо bool должен
    #       возвращать текст результата, флаг is_retry и время сна, чтобы отправить msg пользователю и сделать
    #       asyncio.sleep(some_time), после чего снова сделать resolve_username(...). Также, для избежания спама
    #       надо добавить задержку в 5 секунд перед первым вызовом .resolve_username(...), либо сделать это
    #       прямо внутри .resolve_username(...)
    result_username_exists = await tg_api.resolve_username(username)

    _ = await msg.delete()

    if not result_username_exists.is_found:
        _ = await show_user_not_found(update, context, username)
        return BotConversationState.USERNAME_NOT_FOUND

    ctx.order.target_username = username

    # noinspection PyUnnecessaryCast
    stars_count = cast(int, ctx.order.quantity)
    sbp_price = await star_service.get_order_price(stars_count, "sbp")
    card_price = await star_service.get_order_price(stars_count, "card")

    _ = await show_payment_methods(update, context, sbp_price, card_price, is_gift=True, username=username)

    return BotConversationState.CHOOSE_PAYMENT_GIFT


async def handle_gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен."""
    return await _handle_gift_username_helper(update, context)


@inject
async def _handle_payment_method_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        payment_service: PaymentService
):
    cb_data = cast_callback(PaymentMethodCallback, update.callback_query.data)
    ctx = get_view_context(context)

    ctx.order.payment_method_id = cb_data.method_id

    # noinspection PyUnnecessaryCast
    stars_count = cast(int, ctx.order.quantity)

    # Создаем checkout через сервис
    payment_dto = await payment_service.create_checkout(  # TODO: транзакция должна создаваться в другой момент
        user_id=update.effective_user.id,
        stars_count=stars_count,
        method=cb_data.method_id,
        target_username=ctx.order.target_username
    )

    ctx.order.checkout_transaction_id = str(payment_dto.transaction_id)
    ctx.order.checkout_url = payment_dto.pay_url

    is_gift = ctx.order.recipient_mode == RecipientMode.GIFT

    _ = await show_order_confirmation(
        update, context,
        stars_count, payment_dto.amount, payment_dto.pay_url,
        is_gift, ctx.order.target_username
    )

    return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF


@ensure_use_active_conversation_with_callback
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_payment_method_helper(update, context)
