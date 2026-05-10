from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.active_conversation_checker import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject

from core.services.star_price import StarService
from bot.states import BotConversationState
from bot.context import get_view_context
from bot.callbacks import BackCallback, BackDestination

from bot.handlers.start import start_handler
from bot.renderers.order import (
    show_choose_quantity,
    show_custom_quantity_input,
    show_choose_recipient,
    show_enter_username,
    show_payment_methods
)
from bot.renderers.profile import show_profile_page


@ensure_use_active_conversation_with_callback
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
        return await start_handler(update, context)

    elif dest == BackDestination.CHOOSE_QUANTITY:
        msg = await show_choose_quantity(update)
        ctx.active_conversation = msg
        return BotConversationState.CHOOSE_QUANTITY

    elif dest == BackDestination.CUSTOM_QUANTITY_INPUT:
        msg = await show_custom_quantity_input(update)
        ctx.active_conversation = msg
        return BotConversationState.CUSTOM_QUANTITY_INPUT

    elif dest == BackDestination.CHOOSE_RECIPIENT:
        msg = await show_choose_recipient(update)
        ctx.active_conversation = msg
        return BotConversationState.CHOOSE_RECIPIENT

    elif dest == BackDestination.ENTER_GIFT_USERNAME:
        msg = await show_enter_username(update)
        ctx.active_conversation = msg
        return BotConversationState.ENTER_GIFT_USERNAME

    elif dest in (BackDestination.CHOOSE_PAYMENT_SELF, BackDestination.CHOOSE_PAYMENT_GIFT):
        # При возврате на экран оплаты нам нужно заново рассчитать цены,
        # так как мы не храним их в контексте (цены могут измениться).
        # Берем количество звезд из черновика.
        quantity = ctx.order.quantity
        sbp_price = await star_service.get_order_price(quantity, "sbp")
        card_price = await star_service.get_order_price(quantity, "card")

        is_gift = (dest == BackDestination.CHOOSE_PAYMENT_GIFT)
        username = ctx.order.target_username if is_gift else None

        msg = await show_payment_methods(update, sbp_price, card_price, is_gift=is_gift, username=username)
        ctx.active_conversation = msg

        return BotConversationState.CHOOSE_PAYMENT_GIFT if is_gift else BotConversationState.CHOOSE_PAYMENT_SELF

    elif dest == BackDestination.PROFILE:
        profile_data = ctx.profile_data
        ctx.profile_data = None
        msg = await show_profile_page(update, profile_data)
        ctx.active_conversation = msg
        return BotConversationState.PROFILE

    elif dest == BackDestination.REFERRALS_LIST:
        # Заглушка для возврата к списку рефералов
        # await show_referrals_list(update, referrals_dto)
        return BotConversationState.REFERRALS_LIST