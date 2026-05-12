from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.start import start_handler

from bot.renderers.order import (
    show_choose_quantity,
    show_custom_quantity_input,
    show_choose_recipient,
    show_enter_username,
    show_payment_methods
)
from bot.renderers.profile import show_profile_page

from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.handlers_registry import build_async_handlers_register
from bot.utils.injector import inject
from bot.utils.type_aliases import UpdateWithContextHandler

from bot.callbacks import BackCallback, cast_callback
from bot.context import clear_profile_data, clear_temporary_messages, get_view_context
from bot.enums import BackDestination
from bot.states import BotConversationState

from core.services.star_price import StarService


back_destination_registry: dict[BackDestination, UpdateWithContextHandler[..., BotConversationState]] = {}
register = build_async_handlers_register(back_destination_registry)


@register(BackDestination.MAIN_MENU)
async def _handle_destination_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_profile_data(context)
    return await start_handler(update, context)


@register(BackDestination.CHOOSE_QUANTITY)
async def _handle_destination_choose_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_choose_quantity(update, context)
    return BotConversationState.CHOOSE_QUANTITY


@register(BackDestination.CUSTOM_QUANTITY_INPUT)
async def _handle_destination_custom_quantity_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_custom_quantity_input(update, context)
    return BotConversationState.CUSTOM_QUANTITY_INPUT


@register(BackDestination.CHOOSE_RECIPIENT)
async def _handle_destination_choose_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_choose_recipient(update, context)
    return BotConversationState.CHOOSE_RECIPIENT


@register(BackDestination.ENTER_GIFT_USERNAME)
async def _handle_destination_enter_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ = await show_enter_username(update, context)
    return BotConversationState.ENTER_GIFT_USERNAME


@register(BackDestination.CHOOSE_PAYMENT_SELF, BackDestination.CHOOSE_PAYMENT_GIFT)
@inject
async def _handle_destination_choose_payment(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        star_service: StarService
):
    # При возврате на экран оплаты нам нужно заново рассчитать цены,
    # так как мы не храним их в контексте (цены могут измениться).
    # Берем количество звезд из черновика.
    ctx = get_view_context(context)

    quantity = ctx.order.quantity
    sbp_price = await star_service.get_order_price(quantity, "sbp")
    card_price = await star_service.get_order_price(quantity, "card")

    cb_data = cast_callback(BackCallback, update.callback_query.data)
    is_gift = (cb_data.destination == BackDestination.CHOOSE_PAYMENT_GIFT)
    username = ctx.order.target_username if is_gift else None

    _ = await show_payment_methods(update, context, sbp_price, card_price, is_gift=is_gift, username=username)

    return BotConversationState.CHOOSE_PAYMENT_GIFT if is_gift else BotConversationState.CHOOSE_PAYMENT_SELF


@register(BackDestination.PROFILE)
async def _handle_destination_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)
    profile_data = ctx.profile_data
    _ = await show_profile_page(update, context, profile_data)
    return BotConversationState.PROFILE


@register(BackDestination.REFERRALS_LIST)
async def _handle_destination_referrals_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка для возврата к списку рефералов
    # _ = await show_referrals_list(update, context, referrals_dto)
    return BotConversationState.REFERRALS_LIST


@ensure_use_active_conversation_with_callback
async def handle_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Единый контроллер для обработки всех кнопок 'Назад'.
    Определяет куда вернуться по BackDestination и восстанавливает контекст.
    """
    await clear_temporary_messages(context)

    cb_data = cast_callback(BackCallback, update.callback_query.data)

    handler = back_destination_registry[cb_data.destination]
    return await handler(update, context)
