import json
import logging
from typing import cast
from uuid import UUID

from telegram.ext import ExtBot

from django.conf import settings
from django.utils.crypto import constant_time_compare
from django.http import HttpRequest

from bot.keyboards.error import build_error_kb

from core.domain.enums import TransactionStatus
from core.integrations.platega.schemas import PlategaHeaders, PlategaWebhookRequestJson, PaymentPayloadDict
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
    if request.method != "POST":
        return 405
    if not is_authenticated(request.headers):
        return 403

    return True


def parse_payload(data: PlategaWebhookRequestJson) -> PaymentPayloadDict | None:
    parsed_payload = cast(object, json.loads(data["payload"]))
    if not isinstance(parsed_payload, dict):
        logger.exception("Request from Platega contains payload which is not a dict")
        return None

    if (
            parsed_payload.get("user_id") is None or
            parsed_payload.get("message_id") is None or
            parsed_payload.get("price") is None or
            parsed_payload.get("stars_count") is None or
            parsed_payload.get("target_username") is None
    ):
        logger.exception("Payload from Platega is invalid")
        return None

    return cast(PaymentPayloadDict, cast(object, parsed_payload))


def parse_request(request: HttpRequest) -> tuple[PlategaWebhookRequestJson, PaymentPayloadDict | None]:
    data = cast(PlategaWebhookRequestJson, json.loads(request.body))
    parsed_payload = parse_payload(data)
    return data, parsed_payload


async def get_support_url() -> str:
    async with container() as request_container:
        support_service = await request_container.get(SupportService)
        return await support_service.get_support_url()


async def safe_remove_reply_markup_for_order_message(bot: ExtBot[None], user_id: int, message_id: int) -> None:
    try:
        _ = await bot.edit_message_reply_markup(chat_id=user_id, message_id=message_id, reply_markup=None)
    except Exception as err:
        log_msg = (
            f"Error while trying to remove reply_markup for order message: {user_id = }, {message_id = }\n{err = }"
        )
        logger.exception(log_msg)


async def safe_delete_order_message(bot: ExtBot[None], user_id: int, message_id: int) -> None:
    try:
        _ = await bot.delete_message(chat_id=user_id, message_id=message_id)
    except Exception as err:
        log_msg = (
            f"Error while trying to delete order message: {user_id = }, {message_id = }\n{err = }"
        )
        logger.exception(log_msg)


async def safe_process_transaction(
        data: PlategaWebhookRequestJson, parsed_payload: PaymentPayloadDict | None
) -> str | Transaction | TransactionStatus | None:
    """
    - Если error_msg не None, значит произошла ошибка, тогда второй объект будет None.

    - Перед обработкой будет попытка получить транзакцию - если не получится, будет возвращена ошибка и None.

    - Если транзакция была получена, и она уже SUCCESS, тогда будет возвращено None и None.

    - Далее, если при обработке транзакции ошибки не было, то второй объект будет либо транзакцией, либо
    итоговым статусом на случай проблем с БД.
    """

    try:
        transaction_uuid = UUID(data.get("id"))
    except Exception as uuid_err:
        logger.exception("Couldn't convert transaction id to UUID")
        return f"{uuid_err.__class__.__name__}: {uuid_err}"

    try:
        async with container() as request_container:
            payment_service = await request_container.get(PaymentService)

            transaction = await payment_service.get_transaction_by_uuid(
                transaction_uuid,
                data, parsed_payload
            )
            if transaction is None:
                return f"Couldn't get or create transaction {transaction_uuid}"

            if transaction.status == TransactionStatus.SUCCESS:
                return None

            if data["status"] != "CONFIRMED":
                transaction = await payment_service.cancel_transaction(transaction, data)
            else:
                transaction = await payment_service.confirm_payment(transaction)

            return transaction

    except Exception as transaction_err:
        logger.exception(f"Error during transaction processing:\n{transaction_err = }")
        return f"{transaction_err.__class__.__name__}: {transaction_err}"


async def safe_notify_user(
        bot: ExtBot[None], parse_mode: str,
        transaction: Transaction | TransactionStatus, transaction_id: str,
        user_id: int, support_url: str
) -> None:
    if isinstance(transaction, Transaction) and transaction.status == TransactionStatus.SUCCESS:
            text = (
                f"😊 <b>Заказ успешно доставлен!</b>\n\n"
                f"Пополнили — ⭐ {transaction.amount_stars} звёзд\n"
                f'{"Для кого — @" + transaction.target_username + "\n" if transaction.target_username != "Себе" else ""}\n'
                f"Спасибо за покупку! ❤️\n\n"
                f"✨ <b>Сделать ещё заказ — /start</b>"
            )
            reply_markup = None

    elif isinstance(transaction, TransactionStatus) and transaction == TransactionStatus.SUCCESS:
        text = (
            f"🤕 <b>При обработке заказа возникли трудности...</b>\n\n"
            f"Однако! Звёзды должны быть отправлены 🙏\n"
            f"Если ничего не придёт в течение 5 минут, обратись в тех. поддержку. Извини за неудобства! ❤️\n\n"
            f"✨ <b>Сделать ещё заказ — /start</b>"
        )
        reply_markup = build_error_kb(support_url)

    elif (
            isinstance(transaction, Transaction) and transaction.status == TransactionStatus.CANCELLED
            or transaction == TransactionStatus.CANCELLED
    ):
        text = (
            f"⚠️ <b>Твоему заказу был присвоен статус {TransactionStatus.CANCELLED.translation}</b>\n\n"
            f"Если ты решил не делать заказ, то можешь проигнорировать это сообщение\n\n"
            f"В ином случае обратись в тех. поддержку с ID заказа\n"
            f"🆔 ID заказа: <code>{transaction_id}</code>"
        )
        reply_markup = build_error_kb(support_url)

    else:
        text = (
            f"❌ <b>Произошла ошибка при переводе звёзд!</b>\n\n"
            f"Обратись в тех. поддержку с ID заказа и текстом ошибки\n\n"
            f"🆔 ID заказа: <code>{transaction_id}</code>\n"
        )
        if isinstance(transaction, Transaction):
            text += f"Текст ошибки:\n<pre>{json.dumps(transaction.metadata_info.payload, indent=2)}</pre>"
        else:
            text += "Текст ошибки:\n<pre>Произошла ошибка БД, поэтому полный текст ошибки доступен в логах</pre>"
        reply_markup = build_error_kb(support_url)

    try:
        _ = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup, parse_mode=parse_mode
        )
    except Exception as err:
        logger.exception(f"Error while sending message in bot:\n{err = }")
