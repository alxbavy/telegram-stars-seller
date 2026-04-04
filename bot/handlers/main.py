from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.injector import inject
from bot.states import BotConversationState
from bot.context import clear_order_draft
from bot.callbacks import MainMenuCallback, MainMenuAction
from bot.renderers.base import render_screen
from bot.keyboards.main import build_main_menu_kb, build_support_kb
from bot.stubs import SupportService
from bot.renderers.order import show_choose_quantity


@inject
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_order_draft(context)
    text = "😍 Ты не лэйм! Ты решил брать звёзды у нас — правильный выбор!\n\nЗвёзды дешевле, чем в самом Telegram!\nБери себе или дари друзьям ;)"
    await render_screen(update, text, build_main_menu_kb(), "main_menu.jpg")
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
        text = "💬 Нужна помощь?\n\nАгент поддержки отвечает с 09:00 по 22:00 (МСК).\nПри высокой нагрузке ответ может занять немного больше времени."
        await render_screen(update, text, build_support_kb(url), "support.jpg")
        return BotConversationState.SUPPORT

    elif cb_data.action == MainMenuAction.PROFILE:
        # Здесь должен быть вызов UserService и рендер профиля
        # Для краткости опускаем реализацию профиля, возвращаем стейт
        return BotConversationState.PROFILE
