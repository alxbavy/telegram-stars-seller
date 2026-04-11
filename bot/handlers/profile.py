from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.callbacks import ProfileMenuCallback, ProfileAction, HistoryPageCallback
from bot.renderers.profile import show_order_history_page


@inject
async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cb_data: ProfileMenuCallback = query.data

    if cb_data.action == ProfileAction.HISTORY:
        await show_order_history_page(update, page=1)
        return BotConversationState.ORDER_HISTORY


@inject
async def handle_history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cb_data: HistoryPageCallback = query.data

    await show_order_history_page(update, page=cb_data.page)
    return BotConversationState.ORDER_HISTORY