from typing import cast
from uuid import UUID

from telegram.ext import ContextTypes

from bot.utils.injector import inject_without_update
from core.services.payment import PaymentService


@inject_without_update
async def _clear_specific_transaction_helper(context: ContextTypes.DEFAULT_TYPE, payment_service: PaymentService) -> None:
    """Смотрите документацию для `clear_specific_transaction` для подробностей."""
    transaction_id, expires_in = cast(tuple[UUID, str], context.job.data)
    if not isinstance(transaction_id, UUID):
        raise ValueError("transaction_id must be UUID")
    if not isinstance(expires_in, str):
        raise ValueError("expires_in must be str with format HH:MM:SS")
    await payment_service.delete_transactions(expires_in, transaction_id)


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
