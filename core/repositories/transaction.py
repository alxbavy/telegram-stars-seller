import uuid

from django.db import transaction
from asgiref.sync import sync_to_async
from django.db.models import Sum

from core.domain.enums import TransactionStatus, TransactionType
from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:
    @sync_to_async(thread_sensitive=True)
    def create_transaction(
            self,
            user: TelegramUser,
            amount_fiat: float,
            amount_stars: int,
            payment_method: str,
            target_username: str = None,
            status: str = TransactionStatus.PENDING,
            transaction_type: str = TransactionType.PURCHASE,
            json_payload: dict = None
    ) -> Transaction:
        """
        Raises:
            IntegrityError - если при создании transaction.id UUID будет неуникальным.
        """
        if json_payload is None:
            json_payload = {}

        with transaction.atomic():
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
                payload=json_payload
            )
            return new_transaction

    @sync_to_async(thread_sensitive=True)
    def get_by_transaction_id(self, transaction_id: str | uuid.UUID) -> Transaction | None:
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
        """
        Если transaction_obj был получен не с помощью get_by_transaction_id(...),
        будет сгенерирован дополнительный запрос на получение объекта метаданных,
        так что данную функцию лучше не использовать в цикле с неполными транзакциями.
        """
        metadata = transaction_obj.metadata_info

        metadata.payload.update(new_payload)
        metadata.save(update_fields=["payload"])
        return metadata

    @sync_to_async(thread_sensitive=True)
    def get_user_stats(self, user: TelegramUser) -> dict[str, int]:
        total_stars = Transaction.objects.filter(telegram_user=user).aggregate(Sum("amount_stars"))["amount_stars__sum"]
        orders_count = Transaction.objects.filter(telegram_user=user).count()
        return {
            "total_stars": total_stars if total_stars is not None else 0,
            "orders_count": orders_count,
        }
