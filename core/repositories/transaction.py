import uuid

from django.db import transaction
from asgiref.sync import sync_to_async
from django.db.models import Sum

from core.domain.enums import TransactionStatus, TransactionType
from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:
    @staticmethod
    @sync_to_async(thread_sensitive=True)
    def create_transaction(
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

    @staticmethod
    async def get_by_transaction_id(transaction_id: str | uuid.UUID) -> Transaction | None:
        return await (
            Transaction.objects
            .select_related("metadata_info")
            .filter(id=transaction_id)
            .afirst()
        )

    @staticmethod
    async def get_many_by_username(username: str) -> list[Transaction]:
        return [
            t async for t in Transaction.objects.filter(telegram_user__username=username).order_by("-created_at")
        ]

    # TODO: можно объединить под один get_many(username = None, telegram_id = None), если не будет дополнительной логики
    @staticmethod
    async def get_many_by_telegram_id(telegram_id: int) -> list[Transaction]:
        return [
            t async for t in Transaction.objects.filter(telegram_user__telegram_id=telegram_id).order_by("-created_at")
        ]

    @staticmethod
    async def update_status(transaction_obj: Transaction, new_status: str) -> Transaction:
        transaction_obj.status = new_status
        await transaction_obj.asave(update_fields=["status"])
        return transaction_obj

    @staticmethod
    async def update_payload(transaction_obj: Transaction, new_payload: dict) -> TransactionMetadata:
        """
        Если transaction_obj был получен не с помощью get_by_transaction_id(...),
        будет сгенерирован дополнительный запрос на получение объекта метаданных,
        так что данную функцию лучше не использовать в цикле с неполными транзакциями.
        """
        metadata = transaction_obj.metadata_info

        metadata.payload.update(new_payload)
        await metadata.asave(update_fields=["payload"])
        return metadata

    @staticmethod
    async def get_user_stats(user: TelegramUser) -> dict[str, int]:
        total_stars = (
            await Transaction.objects
            .filter(telegram_user=user)
            .aaggregate(Sum("amount_stars"))
        )["amount_stars__sum"] or 0

        orders_count = await Transaction.objects.filter(telegram_user=user).acount()

        return {
            "total_stars": total_stars,
            "orders_count": orders_count,
        }
