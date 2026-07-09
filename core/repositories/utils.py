from __future__ import annotations

import random
import logging
from typing import overload, Literal
from collections.abc import Awaitable, Callable

from celery import Task

from django.db import OperationalError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from core.domain.network_utils import get_timeout_error_or_none, RetriesEntity


logger = logging.getLogger(__name__)


class DBErrorSafeToRetry(OperationalError):
    """
    Класс ошибок, которые имеет смысл перезапускать.

    Таковыми являются ошибки с текстом `locked`, `busy` и `i/o` (без учёта регистра), так как они все связаны
    с временными ошибками чтения/записи.
    """


class DBErrorCritical(OperationalError):
    """Класс ошибок, которые не имеет смысла перезапускать."""


def _inspect_operational_error(err: OperationalError) -> DBErrorSafeToRetry | DBErrorCritical:
    err_msg = str(err).lower()
    if "locked" in err_msg or "busy" in err_msg or "i/o" in err_msg:
        logger.warning(f"Проблема с чтением БД, ошибка: {err}")
        return DBErrorSafeToRetry(str(err))

    logger.exception(f"Критическая ошибка БД (не блокировка): {err}")
    return DBErrorCritical(str(err))


@overload
def db_action_sync[**P,R](
        func: Callable[P,R], return_exc: Literal[True],
        *args: P.args, **kwargs: P.kwargs
) -> R | DBErrorSafeToRetry | DBErrorCritical: ...


@overload
def db_action_sync[**P,R](
        func: Callable[P, R], return_exc: Literal[False],
        *args: P.args, **kwargs: P.kwargs
) -> R: ...


def db_action_sync[**P,R](
        func: Callable[P,R], return_exc: bool,
        *args: P.args, **kwargs: P.kwargs
) -> R | DBErrorSafeToRetry | DBErrorCritical:
    try:
        return func(*args, **kwargs)

    except OperationalError as err:
        inspected_operational_error = _inspect_operational_error(err)
        if return_exc:
            return inspected_operational_error
        raise inspected_operational_error


@overload
async def db_action_async[R](
        coro: Awaitable[R], return_exc: Literal[True]
) -> R | DBErrorSafeToRetry | DBErrorCritical: ...


@overload
async def db_action_async[R](
        coro: Awaitable[R], return_exc: Literal[False]
) -> R: ...


async def db_action_async[R](coro: Awaitable[R], return_exc: bool) -> R | DBErrorSafeToRetry | DBErrorCritical:
    try:
        return await coro

    except OperationalError as err:
        inspected_operational_error = _inspect_operational_error(err)
        if return_exc:
            return inspected_operational_error
        raise inspected_operational_error


def safe_check_if_retry_db_action[**P,R,DBR](
        celery_task: Task[P,R], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        db_action_result: DBR | OperationalError | DBErrorSafeToRetry | DBErrorCritical, transaction_id: str
) -> DBR | None:
    if isinstance(db_action_result, OperationalError):
        if not isinstance(db_action_result, DBErrorSafeToRetry):
            return None

        timeout_err = get_timeout_error_or_none(
            RetriesEntity.DB_TIME, started_at, timeout,
            f"транзакция {transaction_id}"
        )

        if timeout_err is not None:
            return None  # TODO: можно оповещать пользователя об ошибке, но необязательно

        base_delay = 10.0
        jitter = random.uniform(0.0, 10.0)
        raise celery_task.retry(
            countdown=base_delay + jitter,
            max_retries=None,
            kwargs=celery_kwargs
        )

    return db_action_result


def safe_db_action_sync_with_retries_celery[**FP,FR,**TP,TR](
        func: Callable[FP,FR],
        celery_task: Task[TP,TR], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        transaction_id: str,
        *args: FP.args, **kwargs: FP.kwargs
) -> FR | None:
    return safe_check_if_retry_db_action(
        celery_task, started_at, celery_kwargs, timeout,
        db_action_sync(func, return_exc=True, *args, **kwargs), transaction_id
    )


async def safe_db_action_async_with_retries_celery[FR,**TP,TR](
        coro: Awaitable[FR],
        celery_task: Task[TP,TR], started_at: float, celery_kwargs: dict[str, object], timeout: float,
        transaction_id: str,
) -> FR | None:
    return safe_check_if_retry_db_action(
        celery_task, started_at, celery_kwargs, timeout,
        await db_action_async(coro, return_exc=True), transaction_id
    )


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential_jitter(initial=0.5, max=2.0, jitter=1.0),
    retry=retry_if_exception_type(DBErrorSafeToRetry),
    reraise=True
)
async def db_action_async_with_tenacity[R](coro: Awaitable[R]) -> R:
    return await db_action_async(coro, return_exc=False)


@overload
async def db_action_with_tenacity[R](coro: Awaitable[R], suppress_exc: Literal[False] = False) -> R: ...


@overload
async def db_action_with_tenacity[R](coro: Awaitable[R], suppress_exc: Literal[True]) -> R | None: ...


@overload
async def db_action_with_tenacity[R](coro: Awaitable[R], suppress_exc: bool) -> R | None: ...


async def db_action_with_tenacity[R](coro: Awaitable[R], suppress_exc: Literal[True, False] | bool = False) -> R | None:
    try:
        return await db_action_async_with_tenacity(coro)

    except Exception as err:
        logger.exception(f"{err.__class__.__name__} - {str(err)}")
        if suppress_exc:
            return None
        raise err
