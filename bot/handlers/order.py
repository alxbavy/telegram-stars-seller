from telegram.ext import ContextTypes

from bot.utils.active_conversation_checker import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject
from core.services.star_price import StarService
from core.services.payment import PaymentService
from bot.states import BotConversationState
from bot.context import get_view_context
from bot.renderers.order import *
from core.services.support import SupportService
from core.services.telegram import TelegramService


@ensure_use_active_conversation_with_callback
@inject
async def handle_fixed_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data: FixedQuantityCallback = update.callback_query.data
    ctx = get_view_context(context)
    ctx.order.quantity = cb_data.amount

    msg = await show_choose_recipient(update)
    ctx.active_conversation = msg
    return BotConversationState.CHOOSE_RECIPIENT


@ensure_use_active_conversation_with_callback
@inject
async def handle_custom_quantity_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)
    msg = await show_custom_quantity_input(update)
    ctx.active_conversation = msg
    return BotConversationState.CUSTOM_QUANTITY_INPUT


@inject
async def handle_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                       support_service: SupportService):
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Пожалуйста, введите число.")
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    ctx = get_view_context(context)
    await ctx.active_conversation.delete()

    amount = int(text)
    if amount > 10000:  # Условный лимит
        url = await support_service.get_support_url()
        msg = await show_large_order_warning(update, url)
        ctx.active_conversation = msg
        return BotConversationState.LARGE_ORDER_WARNING

    ctx.order.quantity = amount
    msg = await show_choose_recipient(update)
    ctx.active_conversation = msg
    return BotConversationState.CHOOSE_RECIPIENT


@ensure_use_active_conversation_with_callback
@inject
async def handle_recipient_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, star_service: StarService):
    cb_data: RecipientModeCallback = update.callback_query.data
    ctx = get_view_context(context)
    ctx.order.recipient_mode = cb_data.mode

    if cb_data.mode == RecipientMode.SELF:
        ctx.order.target_username = None
        sbp_price = await star_service.get_order_price(ctx.order.quantity, "sbp")
        card_price = await star_service.get_order_price(ctx.order.quantity, "card")
        msg = await show_payment_methods(update, sbp_price, card_price, is_gift=False)
        ctx.active_conversation = msg
        return BotConversationState.CHOOSE_PAYMENT_SELF
    else:
        msg = await show_enter_username(update)
        ctx.active_conversation = msg
        return BotConversationState.ENTER_GIFT_USERNAME


@inject
async def handle_gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE, tg_api: TelegramService,
                               star_service: StarService):
    username = update.message.text
    # Транзиентный статус 8a

    ctx = get_view_context(context)
    await ctx.active_conversation.delete()

    msg = await update.message.reply_text(f"🔎 Ищем пользователя {username}...\n\nЭто займёт пару секунд.")

    # TODO: может быть такое, что при попытке поиска телеграм заставит подождать клиент telethon, прежде чем
    #       можно будет проверить пользователя -> в таком случае пользователю надо бы вывести сообщение, что
    #       нужно подождать Х времени -> получается, .resolve_username(...) помимо bool должен
    #       возвращать текст результата, флаг is_retry и время сна, чтобы отправить msg пользователю и сделать
    #       asyncio.sleep(some_time), после чего снова сделать resolve_username(...). Также, для избежания спама
    #       надо добавить задержку в 5 секунд перед первым вызовом .resolve_username(...), либо сделать это
    #       прямо внутри .resolve_username(...)
    is_found = await tg_api.resolve_username(username)
    await msg.delete()

    if not is_found:
        msg = await show_user_not_found(update, username)
        ctx.active_conversation = msg
        return BotConversationState.USERNAME_NOT_FOUND

    ctx.order.target_username = username

    sbp_price = await star_service.get_order_price(ctx.order.quantity, "sbp")
    card_price = await star_service.get_order_price(ctx.order.quantity, "card")

    msg = await show_payment_methods(update, sbp_price, card_price, is_gift=True, username=username)
    ctx.active_conversation = msg
    return BotConversationState.CHOOSE_PAYMENT_GIFT


@ensure_use_active_conversation_with_callback
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
    target_username = ctx.order.target_username if ctx.order.target_username else ""
    msg = await show_order_confirmation(
        update,
        ctx.order.quantity, payment_dto.amount, payment_dto.pay_url,
        is_gift, target_username
    )
    ctx.active_conversation = msg

    return BotConversationState.ORDER_CONFIRMATION_GIFT if is_gift else BotConversationState.ORDER_CONFIRMATION_SELF
