import uuid
from typing import List, Optional

from django.db import transaction
from asgiref.sync import sync_to_async

from core.models import TelegramUser, Transaction, TransactionMetadata


class TransactionRepository:

    @sync_to_async(thread_sensitive=True)
    def create_transaction(
            self,
            user_id: int,
            amount_fiat: float,
            amount_stars: int,
            payment_method: str,
            transaction_id: uuid.UUID = None,
            target_username: str = None,
            status: str = "PENDING" # TODO: поменять на Enum.STATUS
    ) -> Transaction:
        if transaction_id is None:
            transaction_id = uuid.uuid4()

        # Используем транзакцию БД: если хоть одна таблица не создастся,
        # откатятся все изменения, чтобы не было "битых" данных
        with transaction.atomic():
            # 1. Находим пользователя (или создаем, если его почему-то нет)
            # TODO: https://docs.djangoproject.com/en/6.0/ref/models/querysets/#methods-that-do-not-return-querysets
            user, _ = TelegramUser.objects.get_or_create(
                telegram_id=user_id,
                # username не обновляем при get, только при create
            )

            # 2. Создаем основную запись транзакции
            new_trans = Transaction.objects.create(
                telegram_user=user,
                amount_fiat=amount_fiat,
                amount_stars=amount_stars,
                status=status,
                target_username=target_username,
                transaction_id=transaction_id  # То самое новое поле UUID
            )

            # 3. Создаем связанные метаданные
            TransactionMetadata.objects.create(
                transaction=new_trans,
                type="PURCHASE",
                payment_method=payment_method,
                payload={}
            )

            return new_trans

    @sync_to_async(thread_sensitive=True)
    def get_by_transaction_id(self, transaction_id: str | uuid.UUID) -> Optional[Transaction]:
        """select_related подтягивает метаданные сразу, чтобы потом не было лишних SQL-запросов"""
        return Transaction.objects.select_related('metadata_info').filter(transaction_id=transaction_id).first()

    @sync_to_async(thread_sensitive=True)
    def get_many_by_username(self, username: str) -> List[Transaction]:
        # Оборачиваем в list(), чтобы Django ВЫПОЛНИЛ запрос прямо сейчас.
        # Если вернуть ленивый QuerySet, он попытается выполниться в асинхронном коде и упадет с ошибкой.
        qs = Transaction.objects.filter(telegram_user__username=username).order_by('-created_at')
        return list(qs)

    @sync_to_async(thread_sensitive=True)
    def get_many_by_telegram_id(self, telegram_id: int) -> List[Transaction]:
        qs = Transaction.objects.filter(telegram_user__telegram_id=telegram_id).order_by('-created_at')
        return list(qs)

    @sync_to_async(thread_sensitive=True)
    def update_status(self, trans_obj: Transaction, status: str) -> Transaction:
        trans_obj.status = status
        # update_fields ускоряет запрос, обновляя только нужное поле
        trans_obj.save(update_fields=['status'])
        return trans_obj

    @sync_to_async(thread_sensitive=True)
    def update_metadata(self, trans_obj: Transaction, metadata: dict) -> TransactionMetadata:
        # Поскольку мы доставали транзакцию через select_related, metadata_info уже в памяти
        meta = trans_obj.metadata_info

        # Обновляем JSON (добавляем новые ключи, не затирая старые)
        meta.payload.update(metadata)
        meta.save(update_fields=['payload'])
        return meta