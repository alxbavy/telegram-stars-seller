from telegram import Update
from telegram.ext import ContextTypes
from bot.states import BotConversationState
from bot.context import clear_order_draft
from bot.renderers.order import show_choose_quantity


async def repeat_order_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Хендлер для кнопки 'Сделать ещё заказ!' (Use Case 10)"""
    await update.callback_query.answer()
    clear_order_draft(context)
    await show_choose_quantity(update)
    return BotConversationState.CHOOSE_QUANTITY
