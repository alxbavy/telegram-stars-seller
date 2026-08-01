from __future__ import annotations

import logging
from uuid import UUID
from decimal import Decimal
from typing import cast, ParamSpec, TypeVar

from telegram import Message

from core.integrations.platega.webhook_utils import (
    safe_get_transaction_with_retries,
    safe_notify_user_about_status_with_retries,
)
from core.domain.enums import TransactionStatus
from core.services.tg_bot import bot
from core.tasks import Task


logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


async def update_order_message_workflow(
        celery_task: Task[P,R],
        parse_mode: str,
        user_id: int,
        message_id: int,
        transaction_id: UUID,
        amount_stars: int,
        price: str,
        target_username: str,
        pay_url: str,
        promo_name: str, promo_discount: str | None,
        *,
        started_at: float
) -> str:
    kwargs = cast(dict[str, object], celery_task.request.kwargs or {}).copy()  # noqa
    kwargs["started_at"] = started_at

    timeout = 900.0  # 15 минут

    transaction = await safe_get_transaction_with_retries(
        celery_task, started_at, kwargs, timeout, transaction_id
    )

    status = transaction.status
    if transaction is None:
        status = TransactionStatus.CANCELLED

    promo_discount_decimal = None
    if promo_discount is not None:
        promo_discount_decimal = Decimal(promo_discount)

    result = await safe_notify_user_about_status_with_retries(
        celery_task, started_at,
        bot, parse_mode,
        user_id, message_id, status, str(transaction_id),
        amount_stars, price,
        target_username, pay_url, promo_name, promo_discount_decimal,
        timeout=timeout
    )

    if isinstance(result, Exception):
        return str(result)

    if isinstance(result, Message):
        return f"message for transaction {transaction_id} is updated"

    if isinstance(result, bool):
        if result:
            return f"message for transaction {transaction_id} is updated"
        return f"message for transaction {transaction_id} is failed to update"

    return str(result)
