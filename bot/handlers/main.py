from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes

from utils import cast_force

from bot.renderers.order import show_choose_quantity
from bot.renderers.support import show_support_page
from bot.renderers.profile import show_profile_page
from bot.renderers.info import show_info_page

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import MainMenuCallback
from bot.context import get_view_context
from bot.enums import MainMenuAction
from bot.states import BotConversationState

from core.repositories.utils import db_action_with_tenacity
from core.services.support import SupportService
from core.services.user import UserService
from core.ioc import inject


main_menu_registry: dict[MainMenuAction, UpdateWithContextHandler[..., BotConversationState]] = {}
register = build_async_handlers_register(main_menu_registry)


@register(MainMenuAction.BUY)
async def _handle_main_menu_action_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_choose_quantity(update, context)
    return BotConversationState.CHOOSE_QUANTITY


@register(MainMenuAction.SUPPORT)
@inject
async def _handle_main_menu_action_support(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        support_service: FromDishka[SupportService]
):
    url = await support_service.get_support_url()
    _ = await show_support_page(update, context, url)
    return BotConversationState.SUPPORT


@register(MainMenuAction.PROFILE)
@inject
async def _handle_main_menu_action_profile(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        user_service: FromDishka[UserService]
):
    profile_data = await db_action_with_tenacity(
        user_service.get_profile_data(update.effective_user.id)
    )
    ctx = get_view_context(context)
    ctx.profile_data = profile_data
    _ = await show_profile_page(update, context, profile_data)
    return BotConversationState.PROFILE


@register(MainMenuAction.INFO)
async def _handle_main_menu_action_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_info_page(update, context)
    return BotConversationState.INFO


@ensure_use_active_conversation_with_callback
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cb_data = cast_force(MainMenuCallback, update.callback_query.data)
    handler = main_menu_registry[cb_data.action]
    return await handler(update, context)
