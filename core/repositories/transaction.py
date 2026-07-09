import json
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Literal, cast, overload
from collections.abc import Mapping, Iterable

from django.db import transaction
from django.db.models import Case, F, When
from django.db.models.functions import Now
from django.utils import timezone
from django.core.exceptions import SynchronousOnlyOperation
from asgiref.sync import sync_to_async

from core.domain.schemas.transaction import TransactionKwargs, TransactionMetaKwargs
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
            pay_url: str,
            message_id: int | None = None,
            promo_id: int | None = None,
            promo_name: str = "",
            promo_discount: Decimal | None = None,
            expires_in: str = "",
            target_username: str = "",
            status: TransactionStatus = TransactionStatus.PENDING,
            transaction_type: str = TransactionType.PURCHASE,
            json_payload: Mapping[str, object] | None = None
    ) -> Transaction:
        """
        Raises:

            IntegrityError - если при создании transaction.id UUID будет неуникальным.
        """

        transaction_kwargs: TransactionKwargs = {
            "id": transaction_id,
            "telegram_user": user,
            "amount_fiat": amount_fiat,
            "amount_stars": amount_stars,
            "status": status,
            "pay_url": pay_url
        }
        if target_username:
            transaction_kwargs["target_username"] = target_username
        if message_id is not None:
            transaction_kwargs["message_id"] = message_id

        expires_in_for_transaction = None
        if expires_in:
            expires_in_datetime = datetime.strptime(expires_in, "%H:%M:%S")
            expires_in_td = timezone.timedelta(
                hours=expires_in_datetime.hour,
                minutes=expires_in_datetime.minute,
                seconds=expires_in_datetime.second
            )
            delay = timezone.timedelta(minutes=30.0)
            expires_in_for_transaction = expires_in_td + delay

        if json_payload is None:
            json_payload = {}
        else:
            json_payload = dict(json_payload)

        metadata_kwargs: TransactionMetaKwargs = {
            "transaction": cast(Transaction, cast(object, None)),
            "type": transaction_type,
            "payment_method": payment_method,
            "payload": json_payload
        }
        if promo_id:
            metadata_kwargs["promo_id"] = promo_id
        if promo_name:
            metadata_kwargs["promo_name"] = promo_name
        if promo_discount:
            metadata_kwargs["promo_discount"] = promo_discount

        with transaction.atomic():
            new_transaction = self.model.objects.create(**transaction_kwargs)

            if expires_in_for_transaction is not None:
                new_transaction.expires_at = new_transaction.created_at + expires_in_for_transaction
                new_transaction.save(update_fields=["expires_at"])

            metadata_kwargs["transaction"] = new_transaction
            meta = self.model_metadata.objects.create(**metadata_kwargs)
            new_transaction.metadata_info = meta

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

    @overload
    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            exclude_status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: Literal[False] = False,
            is_count_only: Literal[False] = False,
            is_select_user: bool = False,
            is_select_metadata: bool = False,
            promo_id: int | None = None,
    ) -> list[Transaction]: ...

    @overload
    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            exclude_status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: Literal[False] = False,
            is_count_only: Literal[True] = True,
            is_select_user: bool = False,
            is_select_metadata: bool = False,
            promo_id: int | None = None,
    ) -> int: ...

    @overload
    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            exclude_status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: Literal[True] = True,
            is_count_only: Literal[False] = False,
            is_select_user: bool = False,
            is_select_metadata: bool = False,
            promo_id: int | None = None,
    ) -> tuple[list[Transaction], int]:
        ...

    @overload
    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            exclude_status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: Literal[True],
            is_count_only: Literal[True] = True,
            is_select_user: bool = False,
            is_select_metadata: bool = False,
            promo_id: int | None = None,
    ) -> int:
        ...

    async def get_many_by(
            self,
            *,
            telegram_id: int | None = None,
            username: str | None = None,
            status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            exclude_status: TransactionStatus | Iterable[TransactionStatus] | None = None,
            start_idx: int | None = None,
            stop_idx: int | None = None,
            is_count: Literal[False, True] | bool = False,
            is_count_only: Literal[False, True] | bool = False,
            is_select_user: bool = False,
            is_select_metadata: bool = False,
            promo_id: int | None = None,
    ) -> list[Transaction] | tuple[list[Transaction], int] | int:
        query = self.model.objects

        if telegram_id is not None:
            query = query.filter(telegram_user__telegram_id=telegram_id)

        if username is not None:
            query = query.filter(telegram_user__username=username)

        if status is not None:
            if isinstance(status, (TransactionStatus, str)):
                query = query.filter(status=status)
            else:
                query = query.filter(status__in=status)

        if exclude_status is not None:
            if isinstance(exclude_status, (TransactionStatus, str)):
                query = query.exclude(status=exclude_status)
            else:
                query = query.exclude(status__in=exclude_status)

        if is_select_user:
            query = query.select_related("telegram_user")

        if is_select_metadata:
            query = query.select_related("metadata_info")

            if promo_id is not None:
                query = query.filter(metadata_info__promo_id=promo_id)

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

    @overload
    async def update(
            self, transaction_obj_or_id: None,
            *,
            new_status: TransactionStatus | None = None, message_id: int | None = None,
            new_payload: Mapping[str, object] | None = None,
            is_count_transaction: bool = True,
            is_count_metadata: bool = True
    ) -> bool: ...

    @overload
    async def update(
            self, transaction_obj_or_id: UUID,
            *,
            new_status: TransactionStatus | None = None, message_id: int | None = None,
            new_payload: Mapping[str, object] | None = None,
            is_count_transaction: bool = True,
            is_count_metadata: bool = True
    ) -> bool: ...

    @overload
    async def update(
            self, transaction_obj_or_id: Transaction,
            *,
            new_status: TransactionStatus | None = None, message_id: int | None = None,
            new_payload: Mapping[str, object] | None = None,
            is_count_transaction: bool = True,
            is_count_metadata: bool = True
    ) -> tuple[bool, Transaction]: ...

    async def update(
            self, transaction_obj_or_id: Transaction | UUID | None,
            *,
            new_status: TransactionStatus | None = None, message_id: int | None = None,
            new_payload: Mapping[str, object] | None = None,
            is_count_transaction: bool = True,
            is_count_metadata: bool = True
    ) -> bool | tuple[bool, Transaction]:
        """
        Обновление по `transaction_id` имеет приоритет над `transaction_obj`.

        Если указан `transaction_id`, будет сделан `SQL-запрос UPDATE`. Это позволяет посчитать кол-во затронутых строк.
        Если новые данные совпадают со старыми, количество затронутых строк будет равно `0`, тогда вернётся `False`.
        Иначе при реальных изменениях в данных вернётся `True`.

        Если обновление идёт с помощью `transaction_obj`, то вернётся `tuple`, где первое значение говорит о том,
        были ли изменения относительно переданного объекта. Второе значение - объект c новыми значениями
        (`.refresh(...)` не применяется).

        Можно настроить, подсчитывать ли изменения в основной транзакции и в метаданных с помощью
        `is_count_transaction` и `is_count_metadata`.

        Если указан `new_payload` и `transaction_obj` был получен без вызова `.select_related("metadata_info")`,
        будет сгенерирован дополнительный запрос на получение объекта метаданных.

        `new_payload` можно обновить без `transaction_obj` с помощью `transaction_id`. Плюсом идёт то, что для этого
        нужен один `SQL-запрос UPDATE`.

        При обновлении с `new_payload`, старый JSON будет перезаписан на `new_payload` (если обновлять через
        `transaction_obj`, то запись будет просто обновлена).
        """

        if transaction_obj_or_id is None:
            return False

        if isinstance(transaction_obj_or_id, UUID):
            updated_main = await self._update_transaction_by_id(
                transaction_obj_or_id,
                new_status=new_status, message_id=message_id,
                is_count_transaction=is_count_transaction
            )
        else:
            updated_main = await self._update_transaction_by_obj(
                transaction_obj_or_id,
                new_status=new_status, message_id=message_id,
                is_count_transaction=is_count_transaction
            )

        if isinstance(updated_main, tuple):
            transaction_obj_or_id = updated_main[1]

        updated_meta = False
        if new_payload is not None:
            new_payload = dict(new_payload)

            if isinstance(transaction_obj_or_id, UUID):
                updated_meta = await self._update_metadata_by_id(
                    transaction_obj_or_id,
                    new_payload=new_payload,
                    is_count_metadata=is_count_metadata
                )
            else:
                updated_meta = await self._update_metadata_by_obj(
                    transaction_obj_or_id,
                    new_payload=new_payload,
                    is_count_metadata=is_count_metadata
                )

        if isinstance(updated_main, tuple) and isinstance(updated_meta, tuple):
            return updated_main[0] or updated_meta[0], updated_meta[1]

        return updated_main or updated_meta

    async def _update_transaction_by_id(
            self,
            transaction_id: UUID,
            *,
            new_status: TransactionStatus | None,
            message_id: int | None,
            is_count_transaction: bool = True
    ) -> bool:
        if new_status is None and message_id is None:
            return False

        new_pairs = (
            ("status", new_status),
            ("message_id", message_id),
        )
        update_fields: dict[str, object] = {k: v for k, v in new_pairs if v is not None}

        exclude_old_data = update_fields.copy()

        if "status" in update_fields:
            update_fields["updated_at"] = Case(
                When(status=new_status, then=F("updated_at")),
                default=Now()
            )

        affected_rows = await (
            self.model.objects
            .filter(id=transaction_id)
            .exclude(**exclude_old_data)
            .aupdate(**update_fields)
        )

        return affected_rows > 0 if is_count_transaction else False

    @staticmethod
    async def _update_transaction_by_obj(
            transaction_obj: Transaction,
            *,
            new_status: TransactionStatus | None,
            message_id: int | None,
            is_count_transaction: bool = True
    ) -> tuple[bool, Transaction]:
        update_fields: set[str] = set()

        if new_status is not None and transaction_obj.status != new_status:
            transaction_obj.status = new_status
            update_fields.add("status")
            update_fields.add("updated_at")

        if message_id is not None:
            transaction_obj.message_id = message_id
            update_fields.add("message_id")

        is_updated = False
        if update_fields:
            await transaction_obj.asave(update_fields=update_fields)
            if is_count_transaction:
                is_updated = True

        return is_updated, transaction_obj

    async def _update_metadata_by_id(
            self,
            transaction_id: UUID,
            *,
            new_payload: dict[str, object],
            is_count_metadata: bool = True
    ) -> bool:
        normalized_payload = json.dumps(new_payload, ensure_ascii=False, sort_keys=True)
        affected_rows = await (
            self.model_metadata.objects
            .filter(transaction__id=transaction_id)
            .exclude(payload__normalize=normalized_payload)
            .aupdate(payload=new_payload)
        )

        return affected_rows > 0 if is_count_metadata else False

    async def _update_metadata_by_obj(
            self,
            transaction_obj: Transaction,
            *,
            new_payload: dict[str, object],
            is_count_metadata: bool = True
    ) -> tuple[bool, Transaction]:
        try:
            metadata = transaction_obj.metadata_info
        except SynchronousOnlyOperation:
            metadata = await self.model_metadata.objects.aget(pk=transaction_obj.metadata_info_id)

        update_fields: set[str] = set()

        if metadata.payload != new_payload:
            metadata.payload.update(new_payload)
            update_fields.add("payload")

        is_updated = False
        if update_fields:
            await metadata.asave(update_fields=["payload"])
            if is_count_metadata:
                is_updated = True

        return is_updated, transaction_obj

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
