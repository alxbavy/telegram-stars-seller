import json
import logging
from typing import TypedDict, cast

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, JsonResponse, HttpResponse

from telegram.ext import ExtBot
from telegram.constants import ParseMode

from bot.keyboards.error import build_error_kb

from core.domain.enums import TransactionStatus
from core.services.payment import PaymentService
from core.services.support import SupportService
from core.business_logic_container import container


logger = logging.getLogger(__name__)


class PlategaRequestJson(TypedDict):
    id: str
    amount: float
    currency: str
    status: str
    paymentMethod: int
    payload: str


@csrf_exempt
async def payment_webhook(request: HttpRequest):  # TODO: протестировать полностью
    """
    Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot.
    """
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    data = cast(PlategaRequestJson, json.loads(request.body))
    parsed_payload = data["payload"].split(" ")
    user_id = int(parsed_payload[0].split("-")[1])
    transaction_id = data.get("id")

    bot: ExtBot[None] = ExtBot(token=settings.TELEGRAM_BOT_TOKEN)
    parse_mode = ParseMode.HTML

    message_id = int(parsed_payload[1].split("-")[1])
    try:
        _ = await bot.delete_message(chat_id=user_id, message_id=message_id)
    except Exception as err:
        logger.exception(f"Error while trying to delete message: {user_id = }, {message_id = }\n{err = }")
        pass

    async with container() as request_container:
        support_service = await request_container.get(SupportService)
        support_url = await support_service.get_support_url()

    try:
        async with container() as request_container:
            payment_service = await request_container.get(PaymentService)
            if data["status"] != "CONFIRMED":
                transaction = await payment_service.cancel_transaction(transaction_id, data)
            else:
                transaction = await payment_service.confirm_payment(transaction_id)
    except Exception as transaction_err:
        text = (
            f"❌ Произошла ошибка. Можно попробовать начать новый заказ или обратиться в тех. поддержку "
            f"с текстом ошибки.\n"
            f"🆔 ID заказа: {transaction_id}\n\n"
            f"Текст ошибки:\n<pre>{err = }</pre>"
        )
        try:
            _ = await bot.send_message(
                chat_id=user_id, text=text,
                reply_markup=build_error_kb(support_url), parse_mode=parse_mode
            )
        except Exception as err:
            logger.exception(f"Error while sending error message in bot:\n{err = }")
            pass
        logger.exception(f"Error during transaction processing:\n{transaction_err = }")
        return HttpResponse(status=200)

    if transaction is None:
        async with container() as request_container:
            payment_service = await request_container.get(PaymentService)

            stars_count = int(parsed_payload[2].split("-")[1])
            target_username = ""
            if len(parsed_payload) == 4:
                target_username = parsed_payload[3].split("-")[1]
            if data["status"] != "CONFIRMED":
                status = TransactionStatus.CANCELLED
            else:
                status = TransactionStatus.SUCCESS

            transaction = await payment_service.create_transaction(
                transaction_id, user_id,
                data["amount"], stars_count,
                "Platega (Generated)", str(data["paymentMethod"]),
                target_username,
                status, data
            )

    if transaction.status == TransactionStatus.SUCCESS:
        text = (
            f"😊 Заказ успешно доставлен!\n\n"
            f"Пополнили — ⭐ {transaction.amount_stars} звёзд\n"
            f'{"Для кого — @" + transaction.target_username + "\n" if transaction.target_username != "Себе" else ""}\n'
            f"Спасибо за покупку! ❤️\n\n"
            f"(Вы можете сделать новый заказ с помощью /start)"
        )
        reply_markup = None
    elif transaction.status == TransactionStatus.CANCELLED:
        text = (
            f"⚠️ Вашему заказу был присвоен статус {TransactionStatus.CANCELLED.translation}.\n\n"
            f"Если вы решили не делать заказ, то можете проигнорировать это сообщение.\n\n"
            f"В ином случае обратитесь в тех. поддержку с ID заказа.\n"
            f"🆔 ID заказа: {transaction_id}"
        )
        reply_markup = build_error_kb(support_url)
    else:
        text = (
            f"❌ Произошла ошибка при переводе звёзд. Обратитесь в тех. поддержку с ID заказа и текстом ошибки.\n\n"
            f"🆔 ID заказа: {transaction_id}\n\n"
            f"Текст ошибки:\n<pre>{json.dumps(transaction.metadata_info.payload, indent=4)}</pre>"
        )
        reply_markup = build_error_kb(support_url)

    try:
        _ = await bot.send_message(
            chat_id=transaction.telegram_user.telegram_id,
            text=text,
            reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception as err:
        logger.exception(f"Error while sending message in bot:\n{err = }")
        pass

    return HttpResponse(status=200)
