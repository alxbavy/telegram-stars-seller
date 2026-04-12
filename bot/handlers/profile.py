from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.callbacks import ProfileAction, HistoryPageCallback
from bot.renderers.profile import show_order_history_page
from core.services.stats import StatsService


@inject
async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, stats_service: StatsService):
    query = update.callback_query
    if query.data.action == ProfileAction.HISTORY:
        history_dto = await stats_service.get_order_history(update.effective_user.id, page=1)
        await show_order_history_page(update, history_dto)
        return BotConversationState.ORDER_HISTORY


@inject
async def handle_history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE, stats_service: StatsService):
    query = update.callback_query
    cb_data: HistoryPageCallback = query.data

    history_dto = await stats_service.get_order_history(update.effective_user.id, page=cb_data.page)
    await show_order_history_page(update, history_dto)
    return BotConversationState.ORDER_HISTORY
