import json
import logging
from enum import StrEnum
from typing import cast, overload, Literal

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.crypto import constant_time_compare

from core.domain.enums import TransactionStatus
from core.integrations.fragment.enums import FragmentStatus
from core.integrations.fragment.schemas import SendStarsResponse
from core.integrations.platega.enums import PlategaStatus
from core.integrations.platega.schemas import PaymentPayloadValidateModel, PlategaWebhookRequestJSON, PaymentPayloadDict
from core.services.redis_service import get_async_redis_client, get_key_fragment_idem


logger = logging.getLogger(__name__)


class ServicesNames(StrEnum):
    PLATEGA = "platega"
    FRAGMENT = "fragment"
    FRAGMENT__FROM_CREATION = "fragment__from_creation"
    FRAGMENT__FROM_WEBHOOK = "fragment__from_webhook"


def validate_fragment_token(request: HttpRequest) -> HttpResponse | None:
    token = request.GET.get("token")
    if not token or not constant_time_compare(token, settings.FRAGMENT_WEBHOOK_SECRET):
        return HttpResponse(status=403)
    return None


async def validate_fragment_idempotency_key(request: HttpRequest) -> HttpResponse | None:
    idem_key = request.headers.get("X-Idempotency-Key")

    if idem_key:
        async_redis_client = get_async_redis_client()
        key = get_key_fragment_idem(idem_key)
        is_new = await async_redis_client.setnx(key, "1")
        if not is_new:
            return HttpResponse(status=200)
        _ = await async_redis_client.expire(key, 172800)  # 48 часов

    return None


def is_platega_authenticated(request: HttpRequest) -> bool:
    merchant_id = request.headers.get("X-MerchantId")
    secret_key = request.headers.get("X-Secret")

    if merchant_id is None or secret_key is None:
        return False
    if (
            not constant_time_compare(str(merchant_id), settings.PLATEGA_MERCHANT_ID) or
            not constant_time_compare(str(secret_key), settings.PLATEGA_SECRET)
    ):
        return False

    return True


async def access_granted_or_http_response(request: HttpRequest, webhook_name: ServicesNames) -> HttpResponse | None:
    if request.method != "POST":
        return HttpResponse(status=405)

    if webhook_name == ServicesNames.PLATEGA:
        if not is_platega_authenticated(request):
            return HttpResponse(status=403)

    if webhook_name == ServicesNames.FRAGMENT:
        http_response = validate_fragment_token(request)
        if http_response is not None:
            return http_response

        http_response = await validate_fragment_idempotency_key(request)
        if http_response is not None:
            return http_response

    return None


def parse_platega_payload(data: PlategaWebhookRequestJSON) -> PaymentPayloadDict | None:
    try:
        parsed_payload = cast(object, json.loads(data["payload"]))
    except Exception as err:
        if data.get("payload", ""):
            logger.exception(f"Couldn't json.loads payload from Platega request:\n{err = }")
        return None

    if not isinstance(parsed_payload, dict):
        logger.exception("Request from Platega contains payload which is not a dict")
        return None

    parsed_payload = cast(PaymentPayloadDict, cast(object, parsed_payload))

    try:
        _ = PaymentPayloadValidateModel(**parsed_payload)
    except Exception as err:
        logger.exception(f"Payload from Platega is invalid:\n{err = }")
        return None

    return parsed_payload


@overload
def parse_request(
        request: HttpRequest, service_name: Literal[ServicesNames.FRAGMENT]
) -> SendStarsResponse: ...


@overload
def parse_request(
        request: HttpRequest, service_name: Literal[ServicesNames.PLATEGA]
) -> tuple[PlategaWebhookRequestJSON, PaymentPayloadDict | None]: ...


def parse_request(
        request: HttpRequest, service_name: ServicesNames
) -> tuple[PlategaWebhookRequestJSON, PaymentPayloadDict | None] | SendStarsResponse:
    if service_name == ServicesNames.PLATEGA:
        data = cast(PlategaWebhookRequestJSON, json.loads(request.body))
        parsed_payload = parse_platega_payload(data)
        return data, parsed_payload

    if service_name == ServicesNames.FRAGMENT:
        return cast(SendStarsResponse, json.loads(request.body))

    raise ValueError(f"Unsupported service: {service_name}")


def transform_into_internal_status_or_keep_original(new_status: str, service_name: ServicesNames) -> TransactionStatus | str:
    if service_name == ServicesNames.PLATEGA:
        return (
            PlategaStatus
            .transform_into_internal_status_or_keep_original(new_status)
        )

    if service_name == ServicesNames.FRAGMENT:
        return (
            FragmentStatus
            .transform_into_internal_status_or_keep_original(new_status)
        )

    return new_status
