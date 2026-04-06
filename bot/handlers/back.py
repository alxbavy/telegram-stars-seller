from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.injector import inject

from core.services.star_price import StarService
from bot.states import BotConversationState
from bot.context import get_view_context, clear_order_draft
from bot.callbacks import BackCallback, BackDestination

from bot.renderers.main import show_main_menu
from bot.renderers.order import (
    show_choose_quantity,
    show_custom_quantity_input,
    show_choose_recipient,
    show_enter_username,
    show_payment_methods
)


@inject
async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE, star_service: StarService):
    """
    Единый контроллер для обработки всех кнопок 'Назад'.
    Определяет куда вернуться по BackDestination и восстанавливает контекст.
    """
    query = update.callback_query
    cb_data: BackCallback = query.data
    dest = cb_data.destination

    ctx = get_view_context(context)

    if dest == BackDestination.MAIN_MENU:
        clear_order_draft(context)
        await show_main_menu(update)
        return BotConversationState.MAIN_MENU

    elif dest == BackDestination.CHOOSE_QUANTITY:
        await show_choose_quantity(update)
        return BotConversationState.CHOOSE_QUANTITY

    elif dest == BackDestination.CUSTOM_QUANTITY_INPUT:
        await show_custom_quantity_input(update)
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    elif dest == BackDestination.CHOOSE_RECIPIENT:
        await show_choose_recipient(update)
        return BotConversationState.CHOOSE_RECIPIENT

    elif dest == BackDestination.ENTER_GIFT_USERNAME:
        await show_enter_username(update)
        return BotConversationState.ENTER_GIFT_USERNAME

    elif dest in (BackDestination.CHOOSE_PAYMENT_SELF, BackDestination.CHOOSE_PAYMENT_GIFT):
        # При возврате на экран оплаты нам нужно заново рассчитать цены,
        # так как мы не храним их в контексте (цены могут измениться).
        # Берем количество звезд из черновика.
        quantity = ctx.order.quantity
        sbp_price = 69.69
        card_price = 69.69

        is_gift = (dest == BackDestination.CHOOSE_PAYMENT_GIFT)
        username = ctx.order.target_username if is_gift else None

        await show_payment_methods(update, sbp_price, card_price, is_gift=is_gift, username=username)

        return BotConversationState.CHOOSE_PAYMENT_GIFT if is_gift else BotConversationState.CHOOSE_PAYMENT_SELF

    elif dest == BackDestination.PROFILE:
        # Заглушка для возврата в профиль
        # await show_profile(update, user_profile_dto)
        return BotConversationState.PROFILE

    elif dest == BackDestination.REFERRALS_LIST:
        # Заглушка для возврата к списку рефералов
        # await show_referrals_list(update, referrals_dto)
        return BotConversationState.REFERRALS_LIST