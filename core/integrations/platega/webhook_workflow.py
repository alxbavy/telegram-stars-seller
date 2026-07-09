from __future__ import annotations

import logging
from uuid import UUID
from decimal import Decimal
from typing import cast

from celery import Task

from core.integrations.platega.webhook_utils import (
    safe_get_transaction_with_retries,
    safe_notify_user_about_status_with_retries,
)
from core.domain.enums import TransactionStatus
from core.services.tg_bot import bot


logger = logging.getLogger(__name__)


async def update_order_message_workflow[**P,R](
        celery_task: Task[P,R],
        parse_mode: str,
        user_id: int,
        message_id: int,
        transaction_id: UUID,
        amount_stars: int,
        price: str,
        target_username: str,
        pay_url: str,
        is_gift: bool,
        promo_name: str, promo_discount: str | None,
        *,
        started_at: float
) -> None:
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

    _ = await safe_notify_user_about_status_with_retries(
        celery_task, started_at,
        bot, parse_mode,
        user_id, message_id, status, str(transaction_id),
        amount_stars, price,
        target_username, pay_url, is_gift, promo_name, promo_discount_decimal,
        timeout=timeout
    )
