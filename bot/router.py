from telegram.ext import ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from bot.handlers.back import handle_back_button
from bot.handlers.profile import handle_profile_menu, handle_history_pagination
from bot.handlers.main import handle_main_menu
from bot.handlers.order import (
    handle_fixed_quantity, handle_custom_quantity_btn, handle_custom_quantity_input,
    handle_recipient_mode, handle_gift_username,
    handle_payment_method,
)
from bot.handlers.start import start_handler, repeat_order_callback
from bot.callbacks import (
    RepeatOrderCallback, MainMenuCallback,
    ProfileMenuCallback, HistoryPageCallback,
    FixedQuantityCallback, CustomQuantityCallback,
    RecipientModeCallback,
    PaymentMethodCallback,
    BackCallback,
)
from bot.states import BotConversationState


def get_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start_handler),
            CallbackQueryHandler(repeat_order_callback, pattern=RepeatOrderCallback)
        ],
        states={
            BotConversationState.MAIN_MENU: [
                CallbackQueryHandler(handle_main_menu, pattern=MainMenuCallback)
            ],
            BotConversationState.INFO: [],
            BotConversationState.PROFILE: [
                CallbackQueryHandler(handle_profile_menu, pattern=ProfileMenuCallback)
            ],
            BotConversationState.ORDER_HISTORY: [
                CallbackQueryHandler(handle_history_pagination, pattern=HistoryPageCallback)
            ],
            BotConversationState.CHOOSE_QUANTITY: [
                CallbackQueryHandler(handle_fixed_quantity, pattern=FixedQuantityCallback),
                CallbackQueryHandler(handle_custom_quantity_btn, pattern=CustomQuantityCallback)
            ],
            BotConversationState.CUSTOM_QUANTITY_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_quantity_input)
            ],
            BotConversationState.CHOOSE_RECIPIENT: [
                CallbackQueryHandler(handle_recipient_mode, pattern=RecipientModeCallback)
            ],
            BotConversationState.ENTER_GIFT_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_gift_username)
            ],
            BotConversationState.CHOOSE_PAYMENT_SELF: [
                CallbackQueryHandler(handle_payment_method, pattern=PaymentMethodCallback)
            ],
            BotConversationState.CHOOSE_PAYMENT_GIFT: [
                CallbackQueryHandler(handle_payment_method, pattern=PaymentMethodCallback)
            ],
            # Состояния подтверждения ждут перехода по URL, бот здесь просто висит
            BotConversationState.ORDER_CONFIRMATION_SELF: [],
            BotConversationState.ORDER_CONFIRMATION_GIFT: [],
        },
        fallbacks=[
            CommandHandler("start", start_handler),
            CallbackQueryHandler(handle_back_button, pattern=BackCallback)
        ],
        name="main_conversation",
        # persistent=True TODO: Uncomment with persistent realisation
    )
