import logging
from typing import cast

from redis import from_url
from redis.lock import Lock
from celery import shared_task

from asgiref.sync import async_to_sync

from telegram.ext import ExtBot
from telegram.constants import ParseMode

from django.conf import settings

from core.domain.enums import TransactionStatus
from core.integrations.platega.schemas import PlategaRequestJson, PaymentPayloadDict
from core.integrations.platega.webhook_utils import (
    get_support_url,
    safe_remove_reply_markup_for_order_message,
    safe_process_transaction,
    safe_notify_user,
)
from core.models import Transaction

from bot.keyboards.error import build_error_kb


logger = logging.getLogger(__name__)


redis_client = from_url(settings.CELERY_BROKER_URL)


@shared_task
def process_payment_background_task(data: PlategaRequestJson, parsed_payload: PaymentPayloadDict | None):
    """
    Эта задача выполнится в фоне воркером Celery.

    В аргументах должны быть объекты, которые могут быть сериализуемые в JSON.
    """

    transaction_id = data.get("id", None)

    if not transaction_id:
        logger.exception("transaction id is missing in platega request")
        return

    lock_name = f"lock_payment_{transaction_id}"
    # timeout - макс. время, сколь замок будет занят; blocking_timeout - время ожидания для ждущих lock
    lock = cast(Lock, redis_client.lock(lock_name, timeout=120, blocking_timeout=110))

    acquired = lock.acquire()

    if not acquired:
        # Если мы не смогли получить замок за 110 секунд, значит первая задача зависла.
        # В контексте дубликата от Платеги - лучше просто прервать эту (вторую) задачу.
        logger.warning(f"Could not acquire lock for {transaction_id}")
        return

    try:
        async_to_sync(run_async_payment_workflow)(data, parsed_payload)
    finally:
        lock.release()


async def run_async_payment_workflow(data: PlategaRequestJson, parsed_payload: PaymentPayloadDict | None):
    bot = ExtBot(token=settings.TELEGRAM_BOT_TOKEN)
    parse_mode = ParseMode.HTML

    result: str | Transaction | TransactionStatus | None = await safe_process_transaction(data, parsed_payload)

    async with bot:
        if parsed_payload:
            await safe_remove_reply_markup_for_order_message(
                bot,
                parsed_payload["user_id"],
                parsed_payload["message_id"]
            )

        if result is None:
            return

        support_url = await get_support_url()

        if isinstance(result, (Transaction, TransactionStatus)) and parsed_payload:
            await safe_notify_user(
                bot, parse_mode,
                result, data.get("id"),
                parsed_payload["user_id"], support_url
            )
            return

        if not parsed_payload:
            return

        text = (
            f"❌ <b>Произошла ошибка!</b>\n\n"
            f"Обратись в тех. поддержку с ID заказа и текстом ошибки или сделай новый заказ — /start\n"
            f"🆔 ID заказа: <code>{data.get('id')}</code>\n\n"
            f"Текст ошибки:\n<pre>{result}</pre>"
        )
        try:
            _ = await bot.send_message(
                chat_id=parsed_payload["user_id"], text=text,
                reply_markup=build_error_kb(support_url), parse_mode=parse_mode
            )
        except Exception as err:
            logger.exception(f"Failed to send error msg: {err}")
