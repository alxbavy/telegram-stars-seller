from telegram import Update
from telegram.ext import ContextTypes

from bot.context import get_view_context
from bot.utils.active_conversation_checker import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.callbacks import ProfileAction, HistoryPageCallback
from bot.renderers.profile import show_order_history_page
from core.services.stats import StatsService


@ensure_use_active_conversation_with_callback
@inject
async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, stats_service: StatsService):
    query = update.callback_query
    ctx = get_view_context(context)
    if query.data.action == ProfileAction.HISTORY:
        history_dto = await stats_service.get_order_history(update.effective_user.id, page=1)
        msg = await show_order_history_page(update, history_dto)
        ctx.active_conversation = msg
        return BotConversationState.ORDER_HISTORY


@ensure_use_active_conversation_with_callback
@inject
async def handle_history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE, stats_service: StatsService):
    query = update.callback_query
    cb_data: HistoryPageCallback = query.data
    ctx = get_view_context(context)

    history_dto = await stats_service.get_order_history(update.effective_user.id, page=cb_data.page)
    msg = await show_order_history_page(update, history_dto)
    ctx.active_conversation = msg
    return BotConversationState.ORDER_HISTORY
