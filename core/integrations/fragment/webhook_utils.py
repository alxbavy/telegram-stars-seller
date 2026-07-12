from __future__ import annotations

import logging
from uuid import UUID
from typing import ParamSpec, TypeVar, overload

from dishka import FromDishka

from core.integrations.fragment.enums import FragmentStatus
from core.repositories.utils import safe_db_action_async_with_retries_celery
from core.services.fragment_transaction import FragmentTransactionService
from core.tasks import Task
from core.ioc import inject
from core.models import FragmentTransaction


logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


@overload
async def safe_create_fragment_tx_with_retries(  # noqa  # pyright: ignore[reportInconsistentOverload]
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, transaction_id: UUID, status: FragmentStatus
) -> FragmentTransaction | None: ...


@inject
async def safe_create_fragment_tx_with_retries(
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, transaction_id: UUID, status: FragmentStatus,
        *,
        fragment_tx_service: FromDishka[FragmentTransactionService]
) -> FragmentTransaction | None:
    transaction = await safe_db_action_async_with_retries_celery(
        fragment_tx_service.create_transaction(fragment_tx_id, transaction_id, status),
        celery_task, started_at, celery_kwargs, timeout,
        str(transaction_id)
    )
    return transaction


@overload
async def unsafe_get_fragment_tx(  # noqa  # pyright: ignore[reportInconsistentOverload]
        fragment_tx_id: UUID
) -> FragmentTransaction | None: ...


@inject
async def unsafe_get_fragment_tx(
        fragment_tx_id: UUID,
        *,
        fragment_tx_service: FromDishka[FragmentTransactionService]
) -> FragmentTransaction | None:
    return await fragment_tx_service.get_by_fragment_id(fragment_tx_id)


async def safe_get_fragment_tx_with_retries(
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


@overload
async def safe_set_status_for_fragment_tx_id_with_retries(  # noqa  # pyright: ignore[reportInconsistentOverload]
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, new_status: FragmentStatus
) -> bool: ...


@inject
async def safe_set_status_for_fragment_tx_id_with_retries(
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        fragment_tx_id: UUID, new_status: FragmentStatus,
        *,
        fragment_tx_service: FromDishka[FragmentTransactionService]
) -> bool:
    is_changed = await safe_db_action_async_with_retries_celery(
        fragment_tx_service.update_status_by_id(fragment_tx_id, new_status),
        celery_task, started_at, celery_kwargs, timeout,
        f"{fragment_tx_id} (fragment)"
    )
    return False if is_changed is None else is_changed
