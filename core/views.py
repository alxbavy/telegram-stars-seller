import asyncio
import json
from random import randint

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse

from telegram.ext import ExtBot
from telegram.constants import ParseMode

from core.integrations.platega.webhook_utils import (
    status_code_or_access_granted,
    parse_request,
    get_support_url,
    safe_delete_order_message,
    safe_process_transaction,
    create_missing_transaction,
    safe_notify_user,
)


@csrf_exempt
async def payment_webhook(request: HttpRequest) -> HttpResponse:  # TODO: протестировать полностью
    """
    Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot.
    """
    status = status_code_or_access_granted(request)
    if type(status) is int:
        return HttpResponse(status=status)

    data, parsed_payload = parse_request(request)
    if parsed_payload is None:
        return HttpResponse(status=200)

    bot: ExtBot[None] = ExtBot(token=settings.TELEGRAM_BOT_TOKEN)
    parse_mode = ParseMode.HTML
    support_url = await get_support_url()

    await safe_delete_order_message(bot, parsed_payload["user_id"], parsed_payload["message_id"])

    is_success, transaction = await safe_process_transaction(
        data,
        bot, parse_mode, parsed_payload["user_id"], support_url
    )
    if not is_success:
        return HttpResponse(status=200)
    if transaction is None:
        transaction = await create_missing_transaction(data, parsed_payload)

    await safe_notify_user(bot, parse_mode, transaction, support_url)
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
