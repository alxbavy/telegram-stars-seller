import asyncio
import json
import logging
from uuid import UUID
from random import randint
from typing import cast

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse

from core.integrations.fragment.schemas import SendStarsResponse
from core.integrations.fragment.tasks import update_fragment_tx_task
from core.integrations.platega.tasks import update_transaction_status_task
from core.integrations.webhook_utils import (
    ServicesNames,
    access_granted_or_http_response,
    parse_request,
    transform_into_internal_status_or_keep_original
)
from core.services.redis_service import (
    async_save_status_by_key, get_lock_latest_status,
    async_acquire_lock
)


logger = logging.getLogger(__name__)


async def _process_webhook(request: HttpRequest, service_name: ServicesNames) -> HttpResponse:
    http_response = await access_granted_or_http_response(request, service_name)
    if http_response is not None:
        return http_response

    parsed_payload = None
    payment_method: str = ""

    raw_new_status: str | None = None
    fragment_tx_id: str | None = None
    if service_name == ServicesNames.PLATEGA:
        platega_data, parsed_payload = parse_request(request, service_name)
        transaction_id = platega_data["id"]
        new_status = transform_into_internal_status_or_keep_original(
            platega_data["status"],
            service_name
        )

        payment_method = str(platega_data["paymentMethod"])

    elif service_name == ServicesNames.FRAGMENT:
        fragment_data: SendStarsResponse = parse_request(request, service_name)
        fragment_tx_id = fragment_data.get("id", None)
        transaction_id = request.GET.get("tx_id")
        raw_new_status = fragment_data["status"]
        new_status = transform_into_internal_status_or_keep_original(
            raw_new_status,
            service_name
        )

    else:
        raise ValueError(f"Unsupported service: {service_name}")

    try:
        transaction_uuid = UUID(transaction_id)
    except Exception as uuid_err:
        logger.exception(f"{uuid_err.__class__.__name__}: {uuid_err}")
        return HttpResponse(status=400)
    transaction_id = cast(str, transaction_id)  # noqa

    async def critical_section() -> None:
        _ = await async_save_status_by_key(service_name, transaction_uuid, str(new_status))
        if fragment_tx_id is not None and raw_new_status is not None:
            _ = await async_save_status_by_key(
                ServicesNames.FRAGMENT__FROM_WEBHOOK, transaction_uuid, raw_new_status
            )
            _ = update_fragment_tx_task.apply_async(
                args=(fragment_tx_id, transaction_id),
                kwargs={"started_at": None}
            )
        _ = update_transaction_status_task.apply_async(
            args=(str(transaction_uuid), parsed_payload, payment_method),
            kwargs={"started_at": None}
        )

    lock = await async_acquire_lock(
        get_lock_latest_status(service_name, transaction_uuid),
        timeout=45.0,
        blocking_timeout=45.0
    )
    if lock is None:
        logger.warning(f"{service_name.capitalize()} webhook: Too many concurrent requests for {transaction_uuid}")
        return HttpResponse(status=429)

    try:
        await critical_section()

    finally:
        try:
            await lock.release()

        except Exception as exc:
            logger.exception(f"{exc.__class__.__name__} - {str(exc)}")

    return HttpResponse(status=200)


@csrf_exempt
async def payment_webhook(request: HttpRequest) -> HttpResponse:
    """Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot."""
    return await _process_webhook(request, ServicesNames.PLATEGA)


@csrf_exempt
async def fragment_webhook(request: HttpRequest) -> HttpResponse:
    return await _process_webhook(request, ServicesNames.FRAGMENT)


running_webhooks: set[int] = set()


@csrf_exempt
async def test_webhook(request: HttpRequest) -> HttpResponse:
    webhook_id = randint(1, 2)
    if webhook_id in running_webhooks:
        print(f"test_webhook {webhook_id} is already running")
        return HttpResponse(status=200)

    print(f"test_webhook {webhook_id} called!")

    print(f"awaiting 5s for {webhook_id}")
    await asyncio.sleep(5)
    print(f"awaited for {webhook_id}")

    headers = dict(request.headers)
    print(json.dumps(headers, indent=2))

    return HttpResponse(status=200)
