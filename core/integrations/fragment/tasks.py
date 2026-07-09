from __future__ import annotations

import time
import logging
from uuid import UUID

from celery import shared_task, Task

from core.integrations.fragment.webhook_workflow import update_fragment_transaction_workflow
from core.integrations.webhook_utils import ServicesNames
from core.services.redis_service import (
    get_and_del_by_key, save_status_by_key,
    get_lock_or_retry, get_lock_fragment_transaction, execute_critical_section_with_lock
)


logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=100)
def update_fragment_tx_task[**P, R](
        self: Task[P,R],
        fragment_tx_id: str,
        transaction_id: str,
        *,
        started_at: float | None
) -> None:
    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        status_from_webhook = get_and_del_by_key(
            ServicesNames.FRAGMENT__FROM_WEBHOOK, transaction_id
        )
        status_from_creation = get_and_del_by_key(
            ServicesNames.FRAGMENT__FROM_CREATION, transaction_id
        )

        if status_from_webhook is not None:
            new_status = status_from_webhook

        elif status_from_creation is not None:
            new_status = status_from_creation

        else:
            debug_msg = (
                f"New status for fragment transaction {fragment_tx_id} (platega {transaction_id}) was already processed"
            )
            logger.debug(debug_msg)
            return None

        is_success: bool = False
        try:
            is_success = await update_fragment_transaction_workflow(
                self, UUID(fragment_tx_id), UUID(transaction_id),
                new_status,
                started_at=started_at
            )

        finally:
            if not is_success:
                if new_status == status_from_webhook:
                    _ = save_status_by_key(
                        ServicesNames.FRAGMENT__FROM_WEBHOOK, transaction_id, new_status,
                        if_not_exists=True
                    )

                elif new_status == status_from_creation:
                    _ = save_status_by_key(
                        ServicesNames.FRAGMENT__FROM_CREATION, transaction_id, new_status,
                        if_not_exists=True
                    )

    lock = get_lock_or_retry(self, get_lock_fragment_transaction(transaction_id))
    return execute_critical_section_with_lock(critical_section, lock)
