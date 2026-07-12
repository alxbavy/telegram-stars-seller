from __future__ import annotations

import time
import logging
from datetime import timedelta
from typing import cast, ParamSpec, TypeVar

from celery import shared_task

from django.utils import timezone

from core.domain.enums import TransactionStatus
from core.repositories.utils import safe_db_action_sync_with_retries_celery
from core.tasks.utils import Task
from core.models import Transaction


logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


def _delete_cancelled_two_weeks_ago_transactions(
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float
) -> tuple[int, dict[str, int]] | None:
    two_weeks_ago = timezone.now() - timedelta(days=14)

    db_action = safe_db_action_sync_with_retries_celery(
        Transaction.objects
        .filter(status=TransactionStatus.CANCELLED, updated_at__lt=two_weeks_ago)
        .delete,
        celery_task, started_at, celery_kwargs, timeout,
        "[МНОЖЕСТВЕННАЯ ОЧИСТКА]"
    )

    return db_action


@shared_task(bind=True, acks_late=True, max_retries=100)
def cleanup_two_week_cancelled_transactions_task(self: Task[P,R], *, started_at: float | None) -> str:
    """Удаляет все транзакции со статусом CANCELLED, которые были обновлены более 14 дней назад."""

    kwargs = cast(dict[str, object], self.request.kwargs or {}).copy()  # noqa

    if started_at is None:
        started_at = time.time()
        kwargs["started_at"] = started_at

    timeout = 300.0  # 5 минут
    result = _delete_cancelled_two_weeks_ago_transactions(
        self, started_at, kwargs, timeout
    )
    if result is None:
        return f"transactions deletion timed out"

    deleted_count, _ = result
    if deleted_count > 0:
        logger.info(f"Сборка мусора: удалено {deleted_count} отмененных транзакций")

    return f"deleted {deleted_count} transactions"
