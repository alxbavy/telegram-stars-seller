from telegram.ext import ContextTypes
from bot.utils.injector import inject
from core.services.star_price import StarService
from core.services.payment import PaymentService
from bot.states import BotConversationState
from bot.context import get_view_context
from bot.renderers.order import *
from core.services.support import SupportService
from core.services.telegram import TelegramService


@inject
async def handle_fixed_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data: FixedQuantityCallback = update.callback_query.data
    ctx = get_view_context(context)
    ctx.order.quantity = cb_data.amount

    await show_choose_recipient(update)
    return BotConversationState.CHOOSE_RECIPIENT


@inject
async def handle_custom_quantity_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_custom_quantity_input(update)
    return BotConversationState.CUSTOM_QUANTITY_INPUT


@inject
async def handle_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       support_service: SupportService):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введите число.")
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    amount = int(text)
    if amount > 10000:  # Условный лимит
        url = await support_service.get_support_url()
        await show_large_order_warning(update, url)
        return BotConversationState.LARGE_ORDER_WARNING

    ctx = get_view_context(context)
    ctx.order.quantity = amount
    await show_choose_recipient(update)
    return BotConversationState.CHOOSE_RECIPIENT


@inject
async def handle_recipient_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, star_service: StarService):
    cb_data: RecipientModeCallback = update.callback_query.data
    ctx = get_view_context(context)
    ctx.order.recipient_mode = cb_data.mode

    if cb_data.mode == RecipientMode.SELF:
        ctx.order.target_username = None
        sbp_price = await star_service.get_order_price(ctx.order.quantity, "sbp")
        card_price = await star_service.get_order_price(ctx.order.quantity, "card")
        await show_payment_methods(update, sbp_price, card_price, is_gift=False)
        return BotConversationState.CHOOSE_PAYMENT_SELF
    else:
        await show_enter_username(update)
        return BotConversationState.ENTER_GIFT_USERNAME


@inject
async def handle_gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_api: TelegramService,
                               star_service: StarService):
    username = update.message.text
    # Транзиентный статус 8a
    msg = await update.message.reply_text("🔎 Ищем пользователя...\n\nЭто займёт пару секунд.")

    is_found = await tg_api.resolve_username(username)
    if not is_found:
        await msg.delete()
        await show_user_not_found(update)
        return BotConversationState.USERNAME_NOT_FOUND

    ctx = get_view_context(context)
    ctx.order.target_username = username

    sbp_price = await star_service.get_order_price(ctx.order.quantity, "sbp")
    card_price = await star_service.get_order_price(ctx.order.quantity, "card")

    await msg.delete()
    await show_payment_methods(update, sbp_price, card_price, is_gift=True, username=username)
    return BotConversationState.CHOOSE_PAYMENT_GIFT


@inject
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_service: PaymentService):
    cb_data: PaymentMethodCallback = update.callback_query.data
    ctx = get_view_context(context)
    ctx.order.payment_method_id = cb_data.method_id

    # Создаем checkout через сервис
    payment_dto = await payment_service.create_checkout(
        user_id=update.effective_user.id,
        stars_count=ctx.order.quantity,
        method=cb_data.method_id,
        target_username=ctx.order.target_username
    )

    ctx.order.checkout_transaction_id = payment_dto.transaction_id
    ctx.order.checkout_url = payment_dto.pay_url

    is_gift = ctx.order.recipient_mode == RecipientMode.GIFT
    await show_order_confirmation(update, ctx.order.quantity, payment_dto.amount, payment_dto.pay_url, is_gift)

    return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF
