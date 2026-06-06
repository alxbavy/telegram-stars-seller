import json
import logging
from typing import cast

from telegram.ext import ExtBot

from django.conf import settings
from django.utils.crypto import constant_time_compare
from django.http import HttpRequest

from bot.keyboards.error import build_error_kb

from core.domain.enums import TransactionStatus
from core.integrations.platega.schemas import PlategaHeaders, PlategaRequestJson, PaymentPayloadDict
from core.services.support import SupportService
from core.services.payment import PaymentService
from core.business_logic_container import container
from core.models import Transaction


logger = logging.getLogger(__name__)


def is_authenticated(headers: PlategaHeaders) -> bool:
    merchant_id = headers.get("X-MerchantId")
    secret_key = headers.get("X-Secret")

    if merchant_id is None or secret_key is None:
        return False
    if (
            not constant_time_compare(str(merchant_id), settings.PLATEGA_MERCHANT_ID) or
            not constant_time_compare(str(secret_key), settings.PLATEGA_SECRET)
    ):
        return False

    return True


def status_code_or_access_granted(request: HttpRequest) -> int | bool:
    if request.method == "POST":
        return 405
    if not is_authenticated(request.headers):
        return 403

    return True


def parse_payload(data: PlategaRequestJson) -> PaymentPayloadDict | None:
    parsed_payload = cast(object, json.loads(data["payload"]))
    if not isinstance(parsed_payload, dict):
        logger.exception("Request from Platega contains payload which is not a dict")
        return None

    if (
            parsed_payload.get("user_id") is None or
            parsed_payload.get("message_id") is None or
            parsed_payload.get("stars_count") is None
    ):
        logger.exception("Payload from Platega is invalid")
        return None

    return cast(PaymentPayloadDict, cast(object, parsed_payload))


def parse_request(request: HttpRequest) -> tuple[PlategaRequestJson, PaymentPayloadDict | None]:
    data = cast(PlategaRequestJson, json.loads(request.body))
    parsed_payload = parse_payload(data)
    return data, parsed_payload


async def get_support_url() -> str:
    async with container() as request_container:
        support_service = await request_container.get(SupportService)
        return await support_service.get_support_url()


async def safe_delete_order_message(bot: ExtBot[None], user_id: int, message_id: int) -> None:
    try:
        _ = await bot.delete_message(chat_id=user_id, message_id=message_id)
    except Exception as err:
        logger.exception(f"Error while trying to delete message: {user_id = }, {message_id = }\n{err = }")
        pass


async def safe_process_transaction(
        data: PlategaRequestJson,
        bot: ExtBot[None], parse_mode: str, user_id: int, support_url: str
) -> tuple[bool, Transaction | None]:
    transaction_id = data.get("id")
    try:
        async with container() as request_container:
            payment_service = await request_container.get(PaymentService)
            if data["status"] != "CONFIRMED":
                transaction = await payment_service.cancel_transaction(transaction_id, data)
            else:
                transaction = await payment_service.confirm_payment(transaction_id)

    except Exception as transaction_err:
        text = (
            f"❌ <b>Произошла ошибка!</b>\n\n"
            f"Обратись в тех. поддержку с ID заказа и текстом ошибки или можешь сделать новый заказ с помощью /start\n"
            f"🆔 ID заказа: <code>{transaction_id}</code>\n\n"
            f"Текст ошибки:\n<pre>{transaction_err.__class__.__name__}: {transaction_err}</pre>"
        )
        try:
            _ = await bot.send_message(
                chat_id=user_id, text=text,
                reply_markup=build_error_kb(support_url), parse_mode=parse_mode
            )
        except Exception as err:
            logger.exception(f"Error while sending error message in bot:\n{err = }")

        logger.exception(f"Error during transaction processing:\n{transaction_err = }")
        return False, None

    return True, transaction


async def create_missing_transaction(data: PlategaRequestJson, parsed_payload: PaymentPayloadDict) -> Transaction:
    async with container() as request_container:
        payment_service = await request_container.get(PaymentService)
        return await payment_service.create_transaction(
            data["id"], parsed_payload["user_id"],
            data["amount"], parsed_payload["stars_count"],
            "Platega (Generated)", str(data["paymentMethod"]),
            parsed_payload.get("target_username", ""),
            TransactionStatus.CANCELLED if data["status"] != "CONFIRMED" else TransactionStatus.SUCCESS,
            data
        )


async def safe_notify_user(bot: ExtBot[None], parse_mode: str, transaction: Transaction, support_url: str) -> None:
    if transaction.status == TransactionStatus.SUCCESS:
        text = (
            f"😊 <b>Заказ успешно доставлен!</b>\n\n"
            f"Пополнили — ⭐ {transaction.amount_stars} звёзд\n"
            f'{"Для кого — @" + transaction.target_username + "\n" if transaction.target_username != "Себе" else ""}\n'
            f"Спасибо за покупку! ❤️\n\n"
            f"✨ <b>Сделать ещё заказ — /start</b>"
        )
        reply_markup = None

    elif transaction.status == TransactionStatus.CANCELLED:
        text = (
            f"⚠️ <b>Твоему заказу был присвоен статус {TransactionStatus.CANCELLED.translation}</b>\n\n"
            f"Если ты решил не делать заказ, то можешь проигнорировать это сообщение\n\n"
            f"В ином случае обратись в тех. поддержку с ID заказа\n"
            f"🆔 ID заказа: <code>{transaction.id}</code>"
        )
        reply_markup = build_error_kb(support_url)

    else:
        text = (
            f"❌ <b>Произошла ошибка при переводе звёзд!</b>\n\n"
            f"Обратись в тех. поддержку с ID заказа и текстом ошибки\n\n"
            f"🆔 ID заказа: <code>{transaction.id}</code>\n"
            f"Текст ошибки:\n<pre>{json.dumps(transaction.metadata_info.payload, indent=2)}</pre>"
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
