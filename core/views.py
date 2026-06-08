import asyncio
import json
from random import randint

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse

from core.integrations.platega.tasks import process_payment_background_task
from core.integrations.platega.webhook_utils import status_code_or_access_granted, parse_request


@csrf_exempt
async def payment_webhook(request: HttpRequest) -> HttpResponse:  # TODO: протестировать полностью
    """
    Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot.
    """
    status = status_code_or_access_granted(request)
    if type(status) is int:
        return HttpResponse(status=status)

    data, parsed_payload = parse_request(request)

    _ = process_payment_background_task.delay(data, parsed_payload)

    return HttpResponse(status=200)


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
