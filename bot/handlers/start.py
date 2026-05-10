from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.main import show_main_menu
from bot.states import BotConversationState
from bot.context import clear_order_draft, get_view_context
from bot.renderers.order import show_choose_quantity


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_order_draft(context)
    msg = await show_main_menu(update)
    ctx = get_view_context(context)
    ctx.active_conversation = msg
    return BotConversationState.MAIN_MENU


async def repeat_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Хендлер для кнопки 'Сделать ещё заказ!' (Use Case 10)"""
    await update.callback_query.answer()
    clear_order_draft(context)
    msg = await show_choose_quantity(update)
    ctx = get_view_context(context)
    ctx.active_conversation = msg
    return BotConversationState.CHOOSE_QUANTITY
