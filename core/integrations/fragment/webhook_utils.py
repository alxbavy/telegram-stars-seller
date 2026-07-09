from __future__ import annotations

import logging
from uuid import UUID

from celery import Task

from core.integrations.fragment.enums import FragmentStatus
from core.repositories.utils import safe_db_action_async_with_retries_celery
from core.services.fragment_transaction import FragmentTransactionService
from core.ioc import get_container
from core.models import FragmentTransaction


logger = logging.getLogger(__name__)


async def safe_create_fragment_tx_with_retries[**P,R](
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, transaction_id: UUID, status: FragmentStatus
) -> FragmentTransaction | None:
    async with get_container()() as request_container:
        fragment_tx_service = await request_container.get(FragmentTransactionService)

        transaction = await safe_db_action_async_with_retries_celery(
            fragment_tx_service.create_transaction(fragment_tx_id, transaction_id, status),
            celery_task, started_at, celery_kwargs, timeout,
            str(transaction_id)
        )

        return transaction


async def unsafe_get_fragment_tx(fragment_tx_id: UUID) -> FragmentTransaction | None:
    async with get_container()() as request_container:
        fragment_tx_service = await request_container.get(FragmentTransactionService)
        return await fragment_tx_service.get_by_fragment_id(fragment_tx_id)


async def safe_get_fragment_tx_with_retries[**P,R](
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID
) -> FragmentTransaction | None:
    """
    Рано или поздно получит транзакцию. Если не получится её найти, или произойдёт тайм-аут, то вернётся `None`
    """
    return await safe_db_action_async_with_retries_celery(
        unsafe_get_fragment_tx(fragment_tx_id),
        celery_task, started_at, celery_kwargs, timeout,
        f"{fragment_tx_id} (fragment)"
    )


async def safe_set_status_for_fragment_tx_id_with_retries[**P, R](
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, new_status: FragmentStatus
) -> bool:
    async with get_container()() as request_container:
        fragment_tx_service = await request_container.get(FragmentTransactionService)

        is_changed = await safe_db_action_async_with_retries_celery(
            fragment_tx_service.update_status_by_id(fragment_tx_id, new_status),
            celery_task, started_at, celery_kwargs, timeout,
            f"{fragment_tx_id} (fragment)"
        )

        return False if is_changed is None else is_changed
