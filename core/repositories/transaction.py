import uuid

from django.db import transaction
from asgiref.sync import sync_to_async

from core.domain.enums import TransactionStatus, TransactionType
from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:
    model = Transaction
    model_metadata = TransactionMetadata

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
            new_transaction = self.model.objects.create(
                telegram_user=user,
                amount_fiat=amount_fiat,
                amount_stars=amount_stars,
                status=status,
                target_username=target_username
            )
            self.model_metadata.objects.create(
                transaction=new_transaction,
                type=transaction_type,
                payment_method=payment_method,
                payload=json_payload
            )
            return new_transaction

    async def get_by_transaction_id(
            self,
            transaction_id: str | uuid.UUID,
            is_select_metadata: bool = True
    ) -> Transaction | None:
        query = self.model.objects.filter(id=transaction_id)
        if is_select_metadata:
            query = query.select_related("metadata_info")
        return await query.afirst()

    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus = None,
            start_idx: int = None,
            stop_idx: int = None,
            is_count: bool = False,
            is_count_only: bool = False,
            is_select_metadata: bool = False
    ) -> tuple[list[Transaction], int] | list[Transaction] | int:
        if telegram_id is None and username is None:
            raise ValueError("telegram_id or username must be provided")

        query = self.model.objects

        if telegram_id is not None:
            query = query.filter(telegram_user__telegram_id=telegram_id)

        if username is not None:
            query = query.filter(telegram_user__username=username)

        if status is not None:
            query = query.filter(status=status)

        if is_select_metadata:
            query = query.select_related("metadata_info")

        query = query.order_by("-created_at")

        if start_idx is not None and stop_idx is not None:
            query = query[start_idx:stop_idx]
        elif start_idx is not None:
            query = query[start_idx:]
        elif stop_idx is not None:
            query = query[:stop_idx]

        if is_count_only:
            return await query.acount()
        elif is_count:
            return [t async for t in query], await query.acount()
        else:
            return [t async for t in query]

    @staticmethod
    async def update_status(transaction_obj: Transaction, new_status: str) -> Transaction:
        transaction_obj.status = new_status
        await transaction_obj.asave(update_fields=["status"])
        return transaction_obj

    @staticmethod
    async def update_payload(transaction_obj: Transaction, new_payload: dict) -> TransactionMetadata:
        """
        Если transaction_obj был получен без вызова .select_related("metadata_info"),
        будет сгенерирован дополнительный запрос на получение объекта метаданных,
        так что данную функцию лучше не использовать в цикле с неполными транзакциями.
        """
        metadata = transaction_obj.metadata_info

        metadata.payload.update(new_payload)
        await metadata.asave(update_fields=["payload"])
        return metadata
