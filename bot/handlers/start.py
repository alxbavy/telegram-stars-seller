from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.main import show_main_menu, send_empty_username_alert
from bot.renderers.order import show_choose_quantity

from bot.context import clear_order_draft
from bot.states import BotConversationState


running_users: set[int] = set()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in running_users:
        return None

    running_users.add(user_id)

    try:
        clear_order_draft(context)

        if update.effective_user.username is None:
            _ = await send_empty_username_alert(update)

        _ = await show_main_menu(update, context)
        return BotConversationState.MAIN_MENU
    finally:
        running_users.discard(user_id)


async def repeat_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Хендлер для кнопки 'Сделать ещё заказ!' (Use Case 10)"""
    clear_order_draft(context)

    if update.effective_user.username is None:
        _ = await send_empty_username_alert(update)

    _ = await show_choose_quantity(update, context)
    return BotConversationState.CHOOSE_QUANTITY
