import asyncio

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot.handlers.back import handle_back_button
from bot.handlers.debug import balance_handler, balance_handler_debug, prices_handler, prices_handler_debug
from bot.handlers.main import handle_main_menu
from bot.handlers.order import (
    handle_fixed_quantity, handle_custom_quantity_btn, handle_custom_quantity_input, handle_order_confirmed,
    handle_recipient_mode, handle_gift_username,
    handle_payment_method,
)
from bot.handlers.profile import handle_profile_menu, handle_history_pagination
from bot.handlers.promo_code import handle_enter_promo, handle_promo_input_request, handle_promo_code_cancel
from bot.handlers.start import start_handler, repeat_order_callback
from bot.handlers.subscription import handle_i_subscribed_button
from bot.callbacks import (
    CancelPromoCodeCallback, RepeatOrderCallback, MainMenuCallback,
    ProfileMenuCallback, HistoryPageCallback,
    FixedQuantityCallback, CustomQuantityCallback,
    RecipientModeCallback,
    PaymentMethodCallback, PromoCodeCallback,
    OrderConfirmedCallback,
    BackCallback, SubscriptionCallback
)
from bot.states import BotConversationState


async def _bot_is_busy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    busy_message = "Бот обрабатывает предыдущее действие, подожди немного..."
    if cb_query := update.callback_query:
        _ = await cb_query.answer(text=busy_message, show_alert=True)
    else:
        _ = await context.bot.send_message(chat_id=update.effective_chat.id, text=busy_message)
        await asyncio.sleep(3)


def get_conversation_handler() -> ConversationHandler[ContextTypes.DEFAULT_TYPE]:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_handler),
            CallbackQueryHandler(repeat_order_callback, pattern=RepeatOrderCallback.pattern),
        ],
        states={
            BotConversationState.NOT_SUBSCRIBED: [
                CallbackQueryHandler(handle_i_subscribed_button, pattern=SubscriptionCallback.pattern)
            ],
            BotConversationState.MAIN_MENU: [
                CallbackQueryHandler(handle_main_menu, pattern=MainMenuCallback.pattern)
            ],
            BotConversationState.INFO: [],
            BotConversationState.SUPPORT: [],
            BotConversationState.PROFILE: [
                CallbackQueryHandler(handle_profile_menu, pattern=ProfileMenuCallback.pattern)
            ],
            BotConversationState.ORDER_HISTORY: [
                CallbackQueryHandler(handle_history_pagination, pattern=HistoryPageCallback.pattern)
            ],
            BotConversationState.CHOOSE_QUANTITY: [
                CallbackQueryHandler(handle_fixed_quantity, pattern=FixedQuantityCallback.pattern),
                CallbackQueryHandler(handle_custom_quantity_btn, pattern=CustomQuantityCallback.pattern)
            ],
            BotConversationState.CUSTOM_QUANTITY_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_quantity_input)
            ],
            BotConversationState.LARGE_ORDER_WARNING: [],
            BotConversationState.CHOOSE_RECIPIENT: [
                CallbackQueryHandler(handle_recipient_mode, pattern=RecipientModeCallback.pattern)
            ],
            BotConversationState.ENTER_GIFT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gift_username)
            ],
            BotConversationState.CHOOSE_PAYMENT: [
                CallbackQueryHandler(handle_payment_method, pattern=PaymentMethodCallback.pattern),
                CallbackQueryHandler(handle_promo_input_request, pattern=PromoCodeCallback.pattern)
            ],
            BotConversationState.ENTER_PROMO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_enter_promo),
                CallbackQueryHandler(handle_promo_code_cancel, pattern=CancelPromoCodeCallback.pattern)
            ],
            BotConversationState.ORDER_CONFIRMATION: [
                CallbackQueryHandler(handle_order_confirmed, pattern=OrderConfirmedCallback.pattern)
            ],
            BotConversationState.ORDER_CONFIRMED: [
                CallbackQueryHandler(repeat_order_callback, pattern=RepeatOrderCallback.pattern)
            ],
            ConversationHandler.WAITING: [  # Временное состояние для асинхронной работы, вход и выход из него контролировать не надо
                MessageHandler(filters.TEXT, _bot_is_busy),
                CallbackQueryHandler(_bot_is_busy)
            ],
        },
        fallbacks=[
            CommandHandler("start", start_handler),
            CallbackQueryHandler(handle_back_button, pattern=BackCallback.pattern),
        ],
        name="main_conversation",
        block=False,
        # persistent=True TODO: Uncomment with persistent realisation
    )

def get_debug_handlers() -> tuple[CommandHandler[ContextTypes.DEFAULT_TYPE, None], ...]:
    return (
        CommandHandler("balance", balance_handler),
        CommandHandler("balance_debug", balance_handler_debug),
        CommandHandler("prices", prices_handler),
        CommandHandler("prices_debug", prices_handler_debug),
    )
