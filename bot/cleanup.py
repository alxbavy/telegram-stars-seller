from uuid import UUID
from typing import cast, overload

from dishka import FromDishka

from telegram.ext import ContextTypes

from core.services.transaction import TransactionService
from core.ioc import inject


# Все методы здесь устаревшие и пока не предполагается их использовать. Очистка делегирована в Celery, и только
# для транзакций со статусом CANCELLED


@overload
async def _clear_expired_transactions_helper() -> None: ...  # noqa  # pyright: ignore[reportInconsistentOverload]


@inject
async def _clear_expired_transactions_helper(*, trans_service: FromDishka[TransactionService]) -> None:
    await trans_service.delete_expired_transactions()


async def clear_expired_transactions(_: ContextTypes.DEFAULT_TYPE) -> None:
    await _clear_expired_transactions_helper()


@overload
async def _clear_specific_transaction_helper(  # noqa  # pyright: ignore[reportInconsistentOverload]
        context: ContextTypes.DEFAULT_TYPE
) -> None: ...


@inject
async def _clear_specific_transaction_helper(
        context: ContextTypes.DEFAULT_TYPE,
        *,
        trans_service: FromDishka[TransactionService]
) -> None:
    """Смотрите документацию для `clear_specific_transaction` для подробностей."""
    job_data = context.job.data
    if not isinstance(job_data, tuple):
        raise ValueError("context.job.data must be tuple")

    if not isinstance(job_data[0], UUID):
        raise ValueError("context.job.data[0] must be UUID")
    if not isinstance(job_data[1], str):
        raise ValueError("context.job.data[1] must be str with format HH:MM:SS")
    transaction_id, expires_in = cast(tuple[UUID, str], job_data)

    await trans_service.delete_transactions_expires_in(expires_in, transaction_id)


async def clear_specific_transaction(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Это `callback`, который должен передаваться в `Job` при создании его с помощью `job_queue`.

    Также, эта функция нуждается в `transaction_id` и `expires_in`, поэтому их надо передать в `data` как объект, который
    можно распаковать (например, `tuple` или `list`).

    `transaction_id` - должен быть uuid.UUID
    `expires_in` - время, отсчитываемое от created_at; должен быть str в формате HH:MM:SS

    Пример::

        _ = context.job_queue.run_once(
            clear_specific_transaction,
            when=expires_in,
            data=(transaction_id, expires_in)
        )
    """
    await _clear_specific_transaction_helper(context)
