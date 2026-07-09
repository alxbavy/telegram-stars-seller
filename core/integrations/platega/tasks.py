from __future__ import annotations

import time
import logging
from uuid import UUID
from typing import cast

from celery import shared_task, Task

from asgiref.sync import async_to_sync

from telegram.constants import ParseMode

from core.domain.enums import TransactionStatus, is_change_status_allowed
from core.integrations.fragment.tasks import update_fragment_tx_task
from core.integrations.platega.schemas import PaymentPayloadDict
from core.integrations.platega.webhook_utils import (
    safe_create_transaction_with_retries,
    safe_get_transaction_with_retries,
    safe_set_status_for_transaction_obj_with_retries,
    safe_set_status_for_transaction_id_with_retries, safe_create_fragment_transaction_if_not_sent_with_retries,
    safe_update_transaction_payload_with_retries
)
from core.integrations.platega.webhook_workflow import (
    update_order_message_workflow
)
from core.integrations.webhook_utils import ServicesNames, transform_into_internal_status_or_keep_original
from core.services.redis_service import (
    acquire_lock, get_lock_or_retry, execute_critical_section_with_lock,
    get_lock_payment_transaction, get_lock_payment_message_polling,
    get_and_del_by_key, save_status_by_key,
)
from core.models import TARGET_SELF


logger = logging.getLogger(__name__)
cleanup_logger = logging.getLogger("cleanup_audit")


@shared_task(bind=True, acks_late=True, max_retries=100)
def process_payment_background_task[**P,R](
        self: Task[P,R],
        transaction_id: str,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float | None
) -> None:
    """
    Эта задача выполнится в фоне воркером Celery.

    В аргументах должны быть объекты, которые могут быть сериализуемые в JSON.
    """

    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        platega_status = get_and_del_by_key(ServicesNames.PLATEGA, transaction_id)
        if isinstance(platega_status, bytes):
            platega_status = platega_status.decode("utf-8")

        fragment_status = get_and_del_by_key(ServicesNames.FRAGMENT, transaction_id)
        if isinstance(fragment_status, bytes):
            fragment_status = fragment_status.decode("utf-8")

        if platega_status is not None and fragment_status is not None:
            if platega_status == TransactionStatus.CHARGEBACKED:
                new_status = platega_status

            else:
                new_status = fragment_status

        elif platega_status is not None:
            new_status = platega_status

        elif fragment_status is not None:
            new_status = fragment_status

        else:
            logger.debug(f"New status for transaction {transaction_id} was already processed")
            return None

        is_success: bool = False
        try:
            is_success = await process_payment_background_workflow(
                self,
                UUID(transaction_id),
                new_status,
                parsed_payload,
                payment_method,
                started_at=started_at
            )

        finally:
            if not is_success:
                if new_status == platega_status:
                    _ = save_status_by_key(
                        ServicesNames.PLATEGA, transaction_id, new_status,
                        if_not_exists=True
                    )

                elif new_status == fragment_status:
                    _ = save_status_by_key(
                        ServicesNames.FRAGMENT, transaction_id, new_status,
                        if_not_exists=True
                    )

    lock = get_lock_or_retry(self, get_lock_payment_transaction(transaction_id))
    return execute_critical_section_with_lock(critical_section, lock)


@shared_task(bind=True, acks_late=True, max_retries=100)
def update_order_message_task[**P,R](
        self: Task[P,R],
        parse_mode: str,
        user_id: int,
        message_id: int,
        transaction_id: str,
        amount_stars: int,
        price: str,
        target_username: str,
        pay_url: str,
        is_gift: bool,
        promo_name: str, promo_discount: str | None,
        *,
        started_at: float | None
) -> None:
    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        await update_order_message_workflow(
            self,
            parse_mode,
            user_id,
            message_id,
            UUID(transaction_id),
            amount_stars,
            price,
            target_username,
            pay_url,
            is_gift,
            promo_name, promo_discount,
            started_at=started_at
        )

    lock = acquire_lock(
        get_lock_payment_message_polling(transaction_id),
        blocking_timeout=5.0
    )
    if lock is None:
        # Если мы не смогли получить замок, значит мы дубликат - можно завершаться
        logger.debug(f"Could not acquire lock for message polling {transaction_id}")
        return None

    return execute_critical_section_with_lock(critical_section, lock)


@shared_task(bind=True, acks_late=True, max_retries=100)
def update_transaction_payload_task[**P,R](
        self: Task[P,R],
        transaction_id: str,
        new_payload: dict[str, object],
        *,
        started_at: float | None
) -> None:
    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        await update_transaction_payload_workflow(
            self,
            UUID(transaction_id),
            new_payload,
            started_at=started_at
        )

    return async_to_sync(critical_section)()


@shared_task(bind=True, acks_late=True, max_retries=100)
def prepare_send_stars_task[**P,R](
        self: Task[P,R],
        transaction_id: str,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float | None
) -> None:
    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        await prepare_send_stars_workflow(
            self,
            UUID(transaction_id),
            parsed_payload,
            payment_method,
            started_at=started_at
        )

    lock = get_lock_or_retry(self, get_lock_payment_transaction(transaction_id))
    return execute_critical_section_with_lock(critical_section, lock)


@shared_task(bind=True, max_retries=100)
def send_stars_task[**P,R](
        self: Task[P,R],
        transaction_id: str,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float | None
) -> None:
    async def critical_section() -> None:
        nonlocal started_at
        if started_at is None:
            started_at = time.time()

        await send_stars_workflow(
            self,
            UUID(transaction_id),
            parsed_payload,
            payment_method,
            started_at=started_at
        )

    lock = get_lock_or_retry(self, get_lock_payment_transaction(transaction_id))
    return execute_critical_section_with_lock(critical_section, lock)


async def prepare_send_stars_workflow[**P,R](
        celery_task: Task[P,R],
        transaction_id: UUID,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float
) -> None:
    kwargs = cast(dict[str, object], celery_task.request.kwargs or {}).copy()  # noqa
    kwargs["started_at"] = started_at

    timeout = 300.0  # 5 минут

    transaction = await safe_get_transaction_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction_id
    )
    if transaction is None:
        return

    new_status = TransactionStatus.SENDING
    if not is_change_status_allowed(transaction.status, new_status):
        _ = update_transaction_payload_task.apply_async(
            args=(str(transaction_id), {"requested_status": new_status}),
            kwargs={"started_at": None}
        )
        return

    is_changed_successfully = await safe_set_status_for_transaction_id_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction_id, new_status
    )
    if not is_changed_successfully:  # Точка невозврата - если статус уже был "В ДОСТАВКЕ", ничего не делаем
        logger.exception(f"Transaction {transaction_id} was already {new_status}")
        return

    _ = send_stars_task.apply_async(
        args=(str(transaction_id), parsed_payload, payment_method),
        kwargs={"started_at": None}
    )


async def send_stars_workflow[**P,R](
        celery_task: Task[P,R],
        transaction_id: UUID,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float
) -> None:
    kwargs = cast(dict[str, object], celery_task.request.kwargs or {}).copy()  # noqa
    kwargs["started_at"] = started_at

    timeout = 600.0  # 10 минут

    transaction = await safe_get_transaction_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction_id
    )
    if transaction is None or transaction.status != TransactionStatus.SENDING:
        return

    send_stars_result = await safe_create_fragment_transaction_if_not_sent_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction
    )
    response = send_stars_result[0]

    new_status = None
    fragment_tx_id = None
    if response is not None:
        new_status = response["status"]
        fragment_tx_id = response.get("id", None)

    if fragment_tx_id is not None and new_status is not None:
        _ = save_status_by_key(ServicesNames.FRAGMENT__FROM_CREATION, transaction_id,new_status)
        _ = update_fragment_tx_task.apply_async(
            args=(str(fragment_tx_id), str(transaction_id)),
            kwargs={"started_at": None}
        )

    if new_status is None:
        new_status = TransactionStatus.IN_DOUBT

    _ = save_status_by_key(
        ServicesNames.FRAGMENT, transaction_id,
        transform_into_internal_status_or_keep_original(new_status, ServicesNames.FRAGMENT),
        if_not_exists=True
    )
    _ = process_payment_background_task.apply_async(
        args=(str(transaction_id), parsed_payload, payment_method),
        kwargs={"started_at": None}
    )

    err_msg = send_stars_result[1]
    if err_msg:
        _ = update_transaction_payload_task.apply_async(
            args=(str(transaction_id), {"err_msg": str(err_msg)}),
            kwargs={"started_at": None}
        )


async def update_transaction_payload_workflow[**P,R](
        celery_task: Task[P,R],
        transaction_id: UUID,
        new_payload: dict[str, object],
        *,
        started_at: float
) -> None:
    kwargs = cast(dict[str, object], celery_task.request.kwargs or {}).copy()  # noqa
    kwargs["started_at"] = started_at

    timeout = 300.0  # 5 минут

    transaction = await safe_get_transaction_with_retries(
        celery_task, started_at, kwargs,
        timeout,
        transaction_id
    )
    if transaction is None:
        return

    _ = await safe_update_transaction_payload_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction, new_payload
    )

    return


async def process_payment_background_workflow[**P,R](
        celery_task: Task[P,R],
        transaction_id: UUID,
        new_status: str,
        parsed_payload: PaymentPayloadDict | None,
        payment_method: str,
        *,
        started_at: float
) -> bool:
    kwargs = cast(dict[str, object], celery_task.request.kwargs or {}).copy()  # noqa
    kwargs["started_at"] = started_at

    timeout = 600.0  # 10 минут

    new_status = cast(TransactionStatus, new_status)

    transaction = await safe_get_transaction_with_retries(
        celery_task, started_at, kwargs,
        timeout,
        transaction_id
    )
    if transaction is None:
        if parsed_payload is None:
            return False

        transaction = await safe_create_transaction_with_retries(
            celery_task, started_at, kwargs, timeout,
            transaction_id, new_status, parsed_payload, payment_method
        )
        if transaction is None:
            return False

    if not is_change_status_allowed(transaction.status, new_status):
        _ = update_transaction_payload_task.apply_async(
            args=(str(transaction_id), {"requested_status": new_status}),
            kwargs={"started_at": None}
        )
        return False

    _, transaction = await safe_set_status_for_transaction_obj_with_retries(
        celery_task, started_at, kwargs, timeout,
        transaction, new_status
    )

    parse_mode = ParseMode.HTML.value

    promo_discount = transaction.metadata_info.promo_discount
    if promo_discount is not None:
        promo_discount = str(promo_discount)

    _ = update_order_message_task.apply_async(
        args=(
            parse_mode,
            transaction.telegram_user.telegram_id,
            transaction.message_id,
            str(transaction_id),
            transaction.amount_stars,
            f"{transaction.amount_fiat:.2f}",
            transaction.target_username,
            transaction.pay_url,
            transaction.target_username not in [TARGET_SELF, transaction.telegram_user.username],
            transaction.metadata_info.promo_name,
            promo_discount
        ),
        kwargs={"started_at": None}
    )

    if new_status == TransactionStatus.PROCESSING:
        _ = prepare_send_stars_task.apply_async(
            args=(str(transaction_id), parsed_payload, payment_method),
            kwargs={"started_at": None}
        )

    elif new_status == TransactionStatus.CANCELLED:
        cleanup_logger.info(f"Транзакция {transaction_id} помечена CANCELLED на удаление")

    return True
