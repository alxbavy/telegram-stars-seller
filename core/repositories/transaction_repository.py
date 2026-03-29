import uuid
from typing import Optional

from django.db import transaction
from asgiref.sync import sync_to_async

from core.domain.enums import TransactionStatus
from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:

    @sync_to_async(thread_sensitive=True)
    def create_transaction(
            self,
            user_id: int,
            amount_fiat: float,
            amount_stars: int,
            payment_method: str,
            target_username: str = None,
            status: str = TransactionStatus.PENDING,
            transaction_type: str = "PURCHASE"
    ) -> Transaction:
        # SQL-транзакция
        with transaction.atomic():
            user = TelegramUser.objects.get(telegram_id=user_id)
            
            new_transaction = Transaction.objects.create(
                telegram_user=user,
                amount_fiat=amount_fiat,
                amount_stars=amount_stars,
                status=status,
                target_username=target_username
            )

            TransactionMetadata.objects.create(
                transaction=new_transaction,
                type=transaction_type,
                payment_method=payment_method,
                payload={}
            )

            return new_transaction

    @sync_to_async(thread_sensitive=True)
    def get_by_transaction_id(self, transaction_id: str | uuid.UUID) -> Optional[Transaction]:
        """select_related подтягивает метаданные сразу, чтобы потом не было лишних SQL-запросов"""
        return Transaction.objects.select_related("metadata_info").filter(transaction_id=transaction_id).first()

    @sync_to_async(thread_sensitive=True)
    def get_many_by_username(self, username: str) -> list[Transaction]:
        # Оборачиваем в list(), чтобы Django ВЫПОЛНИЛ запрос прямо сейчас.
        # Если вернуть ленивый QuerySet, он попытается выполниться в асинхронном коде и упадет с ошибкой.
        qs = Transaction.objects.filter(telegram_user__username=username).order_by("-created_at")
        return list(qs)

    @sync_to_async(thread_sensitive=True)
    def get_many_by_telegram_id(self, telegram_id: int) -> list[Transaction]:
        qs = Transaction.objects.filter(telegram_user__telegram_id=telegram_id).order_by("-created_at")
        return list(qs)

    @sync_to_async(thread_sensitive=True)
    def update_status(self, transaction_obj: Transaction, new_status: str) -> Transaction:
        transaction_obj.status = new_status
        transaction_obj.save(update_fields=["status"])
        return transaction_obj

    @sync_to_async(thread_sensitive=True)
    def update_payload(self, transaction_obj: Transaction, new_payload: dict) -> TransactionMetadata:
        # metadata_info будет получен только в случае, если transaction_obj был получен через get_by_transaction_id
        # TODO: надо проверить получение metadata_info
        metadata = transaction_obj.metadata_info

        metadata.payload.update(new_payload)
        metadata.save(update_fields=["payload"])
        return metadata
