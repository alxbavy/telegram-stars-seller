from telegram import Update
from telegram.ext import ContextTypes

from bot.context import get_view_context
from bot.renderers.info import show_info_page
from bot.renderers.profile import show_profile_page
from bot.renderers.support import show_support_page
from bot.utils.active_conversation_checker import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.callbacks import MainMenuCallback, MainMenuAction
from bot.renderers.order import show_choose_quantity
from core.services.support import SupportService
from core.services.user import UserService


@ensure_use_active_conversation_with_callback
@inject
async def handle_main_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        support_service: SupportService,
        user_service: UserService
):
    query = update.callback_query
    cb_data: MainMenuCallback = query.data
    ctx = get_view_context(context)

    if cb_data.action == MainMenuAction.BUY:
        msg = await show_choose_quantity(update)
        ctx.active_conversation = msg
        return BotConversationState.CHOOSE_QUANTITY

    elif cb_data.action == MainMenuAction.SUPPORT:
        url = await support_service.get_support_url()
        msg = await show_support_page(update, url)
        ctx.active_conversation = msg
        return BotConversationState.SUPPORT

    elif cb_data.action == MainMenuAction.PROFILE:
        profile_data = await user_service.get_profile_data(update.effective_user.id)
        ctx.profile_data = profile_data
        msg = await show_profile_page(update, profile_data)
        ctx.active_conversation = msg
        return BotConversationState.PROFILE

    elif cb_data.action == MainMenuAction.INFO:
        msg = await show_info_page(update)
        ctx.active_conversation = msg
        return BotConversationState.INFO
