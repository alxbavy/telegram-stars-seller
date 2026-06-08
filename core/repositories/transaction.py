from uuid import UUID
from collections.abc import Mapping
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from core.domain.enums import TransactionStatus, TransactionType
from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:
    model: type[Transaction] = Transaction
    model_metadata: type[TransactionMetadata] = TransactionMetadata

    @sync_to_async(thread_sensitive=True)
    def create_transaction(
            self,
            transaction_id: UUID,
            user: TelegramUser,
            amount_fiat: float,
            amount_stars: int,
            payment_method: str,
            expires_in: str = "",
            target_username: str = "",
            status: str = TransactionStatus.PENDING,
            transaction_type: str = TransactionType.PURCHASE,
            json_payload: Mapping[str, object] | None = None
    ) -> Transaction:
        """
        Raises:

            IntegrityError - если при создании transaction.id UUID будет неуникальным.
        """
        with transaction.atomic():
            transaction_kwargs = {
                "id": transaction_id,
                "telegram_user": user,
                "amount_fiat": amount_fiat,
                "amount_stars": amount_stars,
                "status": status,
            }
            if target_username:
                transaction_kwargs["target_username"] = target_username

            new_transaction = self.model.objects.create(**transaction_kwargs)

            if expires_in:
                expires_in_datetime = datetime.strptime(expires_in, "%H:%M:%S")
                expires_in_td = timezone.timedelta(
                    hours=expires_in_datetime.hour,
                    minutes=expires_in_datetime.minute,
                    seconds=expires_in_datetime.second
                )
                delay = timezone.timedelta(minutes=30.0)
                new_transaction.expires_at = new_transaction.created_at + expires_in_td + delay
                new_transaction.save(update_fields=["expires_at"])

            if json_payload is None:
                json_payload = {}

            _ = self.model_metadata.objects.create(
                transaction=new_transaction,
                type=transaction_type,
                payment_method=payment_method,
                payload=json_payload
            )
            return new_transaction

    async def get_by_transaction_id(
            self,
            transaction_id: UUID,
            is_select_user: bool = True,
            is_select_metadata: bool = True
    ) -> Transaction | None:
        query = self.model.objects.filter(id=transaction_id)

        if is_select_user:
            query = query.select_related("telegram_user")

        if is_select_metadata:
            query = query.select_related("metadata_info")

        return await query.afirst()

    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: bool = False,
            is_count_only: bool = False,
            is_select_user: bool = False,
            is_select_metadata: bool = False
    ) -> list[Transaction] | tuple[list[Transaction], int] | int:
        query = self.model.objects

        if telegram_id is not None:
            query = query.filter(telegram_user__telegram_id=telegram_id)

        if username is not None:
            query = query.filter(telegram_user__username=username)

        if status is not None:
            query = query.filter(status=status)

        if is_select_user:
            query = query.select_related("telegram_user")

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
    async def update_payload(transaction_obj: Transaction, new_payload: Mapping[str, object]) -> Transaction:
        """
        Если transaction_obj был получен без вызова .select_related("metadata_info"),
        будет сгенерирован дополнительный запрос на получение объекта метаданных,
        так что данную функцию лучше не использовать в цикле с неполными транзакциями.
        """
        metadata = transaction_obj.metadata_info

        metadata.payload.update(new_payload)
        await metadata.asave(update_fields=["payload"])
        return transaction_obj

    async def delete_expired_transactions(
            self,
            expires_in_td: timezone.timedelta | None,
            transaction_ids: list[UUID] | UUID | None = None
    ):
        """
        Удаляет транзакции (или одну) со статусом PENDING, у которых истекло время ожидания.

        Arguments:

        - `expires_in` - timedelta, время жизни от времени создания транзакции; если None, проверка будет идти по полю
        expired_at у транзакции.

        - `transaction_ids` - list[UUID] | UUID | None, если указано, то удалит либо транзакции с указанными ID,
        либо конкретную транзакцию, иначе удалит все найденные транзакции (в каждом случае проверяется
        статус PENDING и время жизни).
        """

        if expires_in_td is None:
            transactions = self.model.objects.filter(
                status=TransactionStatus.PENDING,
                expires_at__lt=timezone.now()
            )
            _ = await transactions.adelete()
            return

        transactions = self.model.objects.filter(
            status=TransactionStatus.PENDING,
            created_at__lt=timezone.now() - expires_in_td
        )
        if isinstance(transaction_ids, UUID):
            transactions = transactions.filter(id=transaction_ids)
        elif isinstance(transaction_ids, list):
            transactions = transactions.filter(id__in=transaction_ids)

        _ = await transactions.adelete()

    @staticmethod
    async def delete_transaction(transaction_obj: Transaction):
        _ = await transaction_obj.adelete()
