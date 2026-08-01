from typing import overload, Literal

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from bot.renderers.profile import show_order_history_page

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import HistoryPageCallback, ProfileMenuCallback, manage_callback_data
from bot.enums import ProfileAction
from bot.states import BotConversationState

from core.repositories.utils import db_action_with_tenacity
from core.services.stats import StatsService
from core.ioc import inject


profile_registry: dict[ProfileAction, UpdateWithContextHandler[..., BotConversationState]] = {}
register = build_async_handlers_register(profile_registry)


@register(ProfileAction.HISTORY)
@inject
async def _handle_profile_action_history(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        stats_service: FromDishka[StatsService]  # noqa
) -> Literal[BotConversationState.ORDER_HISTORY]:
    history_dto = await db_action_with_tenacity(
        stats_service.get_order_history, update.effective_user.id, page=1
    )
    _ = await show_order_history_page(update, context, history_dto)
    return BotConversationState.ORDER_HISTORY


@ensure_use_active_conversation_with_callback
async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with manage_callback_data(update, ProfileMenuCallback) as cb_data:
        if isinstance(cb_data, int):
            assert cb_data == ConversationHandler.END
            return cb_data

        handler = profile_registry[cb_data.action]
        return await handler(update, context)


@overload
async def _handle_history_pagination_helper(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Literal[BotConversationState.ORDER_HISTORY] | int: ...


@inject
async def _handle_history_pagination_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        stats_service: FromDishka[StatsService]  # noqa
) -> Literal[BotConversationState.ORDER_HISTORY] | int:
    async with manage_callback_data(update, HistoryPageCallback) as cb_data:
        if isinstance(cb_data, int):
            assert cb_data == ConversationHandler.END
            return cb_data

        history_dto = await db_action_with_tenacity(
            stats_service.get_order_history, update.effective_user.id, page=cb_data.page
        )
        _ = await show_order_history_page(update, context, history_dto)
        return BotConversationState.ORDER_HISTORY


@ensure_use_active_conversation_with_callback
async def handle_history_pagination(
        update: Update, context: ContextTypes.DEFAULT_TYPE
) -> Literal[BotConversationState.ORDER_HISTORY] | int:
    return await _handle_history_pagination_helper(update, context)
