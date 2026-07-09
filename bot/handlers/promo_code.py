import logging
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.promo_code import (
    show_enter_promo,
    show_promo_exhaust_for_global,
    show_promo_not_found,
    show_promo_not_active,
    show_promo_exhaust_for_account, show_promo_is_processing,
    show_promo_success
)
from bot.states import BotConversationState
from bot.utils.active_conversation import ensure_use_active_conversation_with_callback
from bot.utils.injector import inject
from bot.context import get_view_context
from bot.enums import RecipientMode

from core.domain.enums import FINAL_MSG_STATUSES
from core.repositories.utils import db_action_with_tenacity
from core.services.promo_code import PromoCodeService
from core.services.transaction import TransactionService
from core.services.redis_service import get_lock_promo_input_processing, acquire_lock
from core.services.user import UserService


logger = logging.getLogger(__name__)


@inject
async def _handle_promo_input_request_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: PromoCodeService
):
    ctx = get_view_context(context)
    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id(update.effective_user.id)
    )
    _ = await show_enter_promo(update, context, ctx.order.recipient_mode == RecipientMode.SELF, active_promo)
    return BotConversationState.ENTER_PROMO


@ensure_use_active_conversation_with_callback
async def handle_promo_input_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_promo_input_request_helper(update, context)


@inject
async def _handle_promo_code_cancel_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        user_service: UserService, promo_service: PromoCodeService
):
    _ = await db_action_with_tenacity(
        user_service.update_active_promo(update.effective_user.id, None)
    )

    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id(update.effective_user.id)
    )

    ctx = get_view_context(context)
    _ = await show_enter_promo(update, context, ctx.order.recipient_mode == RecipientMode.SELF, active_promo)
    return BotConversationState.ENTER_PROMO


@ensure_use_active_conversation_with_callback
async def handle_promo_code_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_promo_code_cancel_helper(update, context)


@inject
async def _handle_enter_promo_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        *,
        promo_service: PromoCodeService,
        trans_service: TransactionService,
        user_service: UserService
):
    promo_name = cast(str, update.message.text)  # noqa
    found_promo = await db_action_with_tenacity(
        promo_service.get_promo_by_name(promo_name)
    )

    if found_promo is None:
        _ = await show_promo_not_found(update, promo_name)
        return BotConversationState.ENTER_PROMO

    if not found_promo.is_active:
        _ = await show_promo_not_active(update, promo_name)
        return BotConversationState.ENTER_PROMO

    lock_promo = acquire_lock(
        get_lock_promo_input_processing(), blocking_timeout=30.0
    )

    if lock_promo is None:
        _ = await show_promo_is_processing(update)
        return BotConversationState.ENTER_PROMO

    try:
        transactions_with_promo, tx_with_promo_count = await db_action_with_tenacity(
            trans_service.get_processing_or_succeeded_transactions(found_promo.id)
        )

        usage_left_account = 9999

        if found_promo.usage_account is not None:
            usage_account = sum(
                (1 for tx in transactions_with_promo if tx.telegram_user.telegram_id == update.effective_user.id)
            )

            if usage_account >= found_promo.usage_account:
                is_hold = False
                for tx in transactions_with_promo:
                    if tx.telegram_user.telegram_id == update.effective_user.id and tx.status not in FINAL_MSG_STATUSES:
                        is_hold = True
                        break

                _ = await show_promo_exhaust_for_account(update, promo_name, is_hold)
                return BotConversationState.ENTER_PROMO

            usage_left_account = found_promo.usage_account - usage_account

        if found_promo.usage_global is not None:
            users_with_promo_count = await db_action_with_tenacity(
                user_service.get_users_with_promo_id_count(found_promo.id)
            )

            usage_global = users_with_promo_count + tx_with_promo_count
            if usage_global >= found_promo.usage_global:
                is_hold = False
                for tx in transactions_with_promo:
                    if tx.status not in FINAL_MSG_STATUSES:
                        is_hold = True
                        break

                _ = await show_promo_exhaust_for_global(update, found_promo.name, is_hold)
                return BotConversationState.ENTER_PROMO

            usage_left_account = min(usage_left_account, found_promo.usage_global - usage_global)

        _ = await db_action_with_tenacity(
            user_service.update_active_promo(update.effective_user.id, found_promo)
        )

        ctx = get_view_context(context)
        _ = await show_promo_success(
            update, context,
            ctx.order.recipient_mode == RecipientMode.SELF, found_promo, usage_left_account
        )

    finally:
        try:
            lock_promo.release()

        except Exception as exc:
            logger.exception(f"{exc.__class__.__name__} - {str(exc)}")
            pass

    return BotConversationState.ENTER_PROMO


# Срабатывает на ввод пользователя, поэтому @ensure_use_active_conversation_with_callback не нужен
async def handle_enter_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _handle_enter_promo_helper(update, context)
