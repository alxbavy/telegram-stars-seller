from __future__ import annotations

import random
import logging
from uuid import UUID
from typing import Protocol, cast
from collections.abc import Sequence

from django.conf import settings

from redis import from_url  # noqa
from redis.lock import Lock  # noqa

from celery import Task


logger = logging.getLogger(__name__)


redis_client = from_url(settings.CELERY_BROKER_URL, decode_responses=True)


LOCK_PAYMENT = "lock_payment"
MESSAGE_POLLING = "message_polling"
LATEST_STATUS = "latest_status"
LOCK_LATEST_STATUS = f"lock_{LATEST_STATUS}"

LOCK_FRAGMENT = "lock_fragment"
FRAGMENT_IDEM_KEY = "fragment_idem_key"

LOCK_PROMO_INPUT_PROCESSING = "lock_promo_input_processing"


# TODO: протестировать вне вебхука
_lua_get_and_del = """
local val = redis.call('GET', KEYS[1])
if val and val ~= '' then
    redis.call('DEL', KEYS[1])
    return val
else
    return nil
end
"""

class _GetAndDel(Protocol):
    def __call__(self, keys: Sequence[str]) -> str | None: ...

get_and_del: _GetAndDel = redis_client.register_script(_lua_get_and_del)


def get_lock_latest_status(service_name: str, transaction_id: str | UUID) -> str:
    return f"{LOCK_LATEST_STATUS}:{service_name}:{transaction_id}"


def get_lock_payment_transaction(transaction_id: str | UUID) -> str:
    return f"{LOCK_PAYMENT}:{transaction_id}"


def get_lock_payment_message_polling(transaction_id: str | UUID) -> str:
    return f"{LOCK_PAYMENT}:{transaction_id}:{MESSAGE_POLLING}"


def get_lock_fragment_transaction(transaction_id: str | UUID) -> str:
    return f"{LOCK_FRAGMENT}:{transaction_id}"


def get_lock_promo_input_processing() -> str:
    return f"{LOCK_PROMO_INPUT_PROCESSING}"


def get_key_latest_status(service_name: str, transaction_id: str | UUID) -> str:
    return f"{LATEST_STATUS}:{service_name}:{transaction_id}"


def get_key_fragment_idem(idem_key: str) -> str:
    return f"{FRAGMENT_IDEM_KEY}:{idem_key}"


def save_status_by_key(
        service_name: str, transaction_id: str | UUID, status: str,
        *,
        if_not_exists: bool = False
) -> bool:
    """
    Если `if_not_exists` равен `True`, то будет `redis_client.set(nx=True)`, что означает сохранить статус только если
    такого ключа не существует.
    """
    key = get_key_latest_status(service_name, transaction_id)
    return cast(bool, redis_client.set(key, status, ex=172800, nx=if_not_exists))  # 48 часов  # noqa


def get_and_del_by_key(service_name: str, transaction_id: str | UUID) -> str | None:
    key = get_key_latest_status(service_name, transaction_id)
    return get_and_del(keys=[key])


def acquire_lock(
        lock_name: str,
        timeout: float = 180.0,
        blocking: bool = True, blocking_timeout: float = 10.0
) -> Lock | None:
    lock = cast(Lock, redis_client.lock(
        lock_name,
        timeout=timeout,
        blocking=blocking, blocking_timeout=blocking_timeout
    ))

    if not lock.acquire():
        return None

    return lock


def get_lock_or_retry[**P,R](
        celery_task: Task[P,R],
        lock_name: str,
        base_delay: float = 5.0, max_jitter: float = 3.0, timeout: float = 180.0, blocking_timeout: float = 10.0
) -> Lock:
    lock = acquire_lock(lock_name, timeout, blocking_timeout)

    if lock is None:
        jitter = random.uniform(0.0, abs(max_jitter))
        raise celery_task.retry(countdown=base_delay + jitter, max_retries=None)

    return lock
