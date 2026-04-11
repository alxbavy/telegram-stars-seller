from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.main import show_main_menu
from bot.renderers.support import show_support_page
from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.context import clear_order_draft
from bot.callbacks import MainMenuCallback, MainMenuAction
from bot.renderers.base import render_screen
from bot.keyboards.main import build_main_menu_kb, build_support_kb
from bot.renderers.order import show_choose_quantity
from core.services.support import SupportService


@inject
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update)
    return BotConversationState.MAIN_MENU


@inject
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, support_service: SupportService):
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
        # Здесь должен быть вызов UserService и рендер профиля
        # Для краткости опускаем реализацию профиля, возвращаем стейт
        return BotConversationState.PROFILE
