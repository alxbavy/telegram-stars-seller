from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.profile import show_order_history_page

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.injector import inject
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import HistoryPageCallback, cast_callback, ProfileMenuCallback
from bot.enums import ProfileAction
from bot.states import BotConversationState

from core.services.stats import StatsService


profile_registry: dict[ProfileAction, UpdateWithContextHandler[..., BotConversationState]] = {}
register = build_async_handlers_register(profile_registry)


@register(ProfileAction.HISTORY)
@inject
async def _handle_profile_action_history(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        stats_service: StatsService
):
    history_dto = await stats_service.get_order_history(update.effective_user.id, page=1)
    _ = await show_order_history_page(update, context, history_dto)
    return BotConversationState.ORDER_HISTORY


@ensure_use_active_conversation_with_callback
async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data = cast_callback(ProfileMenuCallback, update.callback_query.data)
    handler = profile_registry[cb_data.action]
    return await handler(update, context)


@inject
async def _handle_history_pagination_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        stats_service: StatsService
):
    cb_data = cast_callback(HistoryPageCallback, update.callback_query.data)

    history_dto = await stats_service.get_order_history(update.effective_user.id, page=cb_data.page)
    _ = await show_order_history_page(update, context, history_dto)
    return BotConversationState.ORDER_HISTORY


@ensure_use_active_conversation_with_callback
async def handle_history_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_history_pagination_helper(update, context)
