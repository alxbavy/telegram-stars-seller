from __future__ import annotations

import time
import logging
from datetime import timedelta
from typing import cast

from celery import shared_task, Task

from django.utils import timezone

from core.repositories.utils import safe_db_action_sync_with_retries_celery
from core.models import TelegramUser


logger = logging.getLogger(__name__)


def _deactivate_unused_promo_codes[**P,R](
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float
) -> int | None:
    one_day_ago = timezone.now() - timedelta(days=1)

    db_action = safe_db_action_sync_with_retries_celery(
        TelegramUser.objects
        .filter(active_promo__isnull=False, promo_since__lt=one_day_ago)
        .update,
        celery_task, started_at, celery_kwargs, timeout,
        "[ДЕАКТИВАЦИЯ ПРОМОКОДОВ]",
        active_promo=None, promo_since=None
    )

    return db_action


@shared_task(bind=True, acks_late=True, max_retries=100)
def deactivate_unused_promo_codes_task[**P,R](self: Task[P,R], *, started_at: float | None) -> str:
    """Деактивирует у пользователей активные промокоды, которые были активированы больше суток назад."""

    kwargs = cast(dict[str, object], self.request.kwargs or {}).copy()  # noqa

    if started_at is None:
        started_at = time.time()
        kwargs["started_at"] = started_at

    timeout = 300.0  # 5 минут
    result = _deactivate_unused_promo_codes(self, started_at, kwargs, timeout)
    if result is None:
        return f"promo deactivations timed out"

    deactivated_promos_count = result

    if deactivated_promos_count > 0:
        logger.info(f"Сборка мусора: деактивировано {deactivated_promos_count} неиспользованных промокодов")

    return f"deactivated {deactivated_promos_count} promo codes"
