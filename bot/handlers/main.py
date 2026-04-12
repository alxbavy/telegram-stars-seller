from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.info import show_info_page
from bot.renderers.main import show_main_menu
from bot.renderers.profile import show_profile_page
from bot.renderers.support import show_support_page
from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.callbacks import MainMenuCallback, MainMenuAction
from bot.renderers.order import show_choose_quantity
from core.services.support import SupportService
from core.services.user import UserService


@inject
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update)
    return BotConversationState.MAIN_MENU


@inject
async def handle_main_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        support_service: SupportService,
        user_service: UserService
):
    query = update.callback_query
    cb_data: MainMenuCallback = query.data

    if cb_data.action == MainMenuAction.BUY:
        await show_choose_quantity(update)
        return BotConversationState.CHOOSE_QUANTITY

    elif cb_data.action == MainMenuAction.SUPPORT:
        url = await support_service.get_support_url()
        await show_support_page(update, url)
        return BotConversationState.SUPPORT

    elif cb_data.action == MainMenuAction.PROFILE:
        profile_data = await user_service.get_profile_data(update.effective_user.id)
        await show_profile_page(update, profile_data)
        return BotConversationState.PROFILE

    elif cb_data.action == MainMenuAction.INFO:
        await show_info_page(update)
        return BotConversationState.INFO
