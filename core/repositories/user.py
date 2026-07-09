from datetime import datetime
from typing import Literal, overload

from django.db.models import Sum
from django.db.models.functions import Now

from core.domain.enums import TransactionStatus
from core.dto.user import UserProfileDTO
from core.models import PromoCode, TelegramUser


class UserRepository:
    model: type[TelegramUser] = TelegramUser

    async def create_telegram_user(self, telegram_id: int, username: str) -> TelegramUser:
        return await self.model.objects.acreate(telegram_id=telegram_id, username=username)

    async def get_by_telegram_id(
            self,
            telegram_id: int,
            is_prefetch_transactions: bool = False,
            is_select_promo: bool = False
    ) -> TelegramUser | None:
        query = self.model.objects.filter(telegram_id=telegram_id)

        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")

        if is_select_promo:
            query = query.select_related("active_promo")

        return await query.afirst()

    async def get_by_username(
            self,
            username: str,
            is_prefetch_transactions: bool = False,
            is_select_promo: bool = False
    ) -> TelegramUser | None:
        clean_username = username.lstrip("@")
        query = self.model.objects.filter(username=clean_username)

        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")

        if is_select_promo:
            query = query.select_related("active_promo")

        return await query.afirst()

    @overload
    async def get_many_by(
            self,
            start_date: datetime | None = None,
            end_date: datetime | None = None,
            is_count_only: Literal[False] = False,
            is_prefetch_transactions: bool = False,
            is_select_promo: bool = False,
            promo_id: int | None = None,
    ) -> list[TelegramUser]: ...

    @overload
    async def get_many_by(
            self,
            start_date: datetime | None = None,
            end_date: datetime | None = None,
            is_count_only: Literal[True] = True,
            is_prefetch_transactions: bool = False,
            is_select_promo: bool = False,
            promo_id: int | None = None,
    ) -> int: ...

    async def get_many_by(
            self,
            start_date: datetime | None = None,
            end_date: datetime | None = None,
            is_count_only: Literal[False, True] | bool = False,
            is_prefetch_transactions: bool = False,
            is_select_promo: bool = False,
            promo_id: int | None = None,
    ) -> list[TelegramUser] | int:
        query = self.model.objects

        if start_date is not None and end_date is not None:
            query = query.filter(created_at__range=(start_date, end_date))
        elif start_date is not None:
            query = query.filter(created_at__gte=start_date)
        elif end_date is not None:
            query = query.filter(created_at__lte=end_date)

        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")

        if is_select_promo:
            query = query.select_related("active_promo")

            if promo_id is not None:
                query = query.filter(active_promo__id=promo_id)

        query = query.order_by("-created_at")

        if is_count_only:
            return await query.acount()

        return [user async for user in query]

    async def get_user_stats(self, telegram_id: int) -> UserProfileDTO | None:
        user = await self.get_by_telegram_id(telegram_id, is_prefetch_transactions=True)

        if user is None:
            return None

        success_orders = user.transactions.filter(status=TransactionStatus.SUCCESS)
        total_stars = (await success_orders.aaggregate(Sum("amount_stars")))["amount_stars__sum"] or 0
        orders_count = await success_orders.acount()

        return UserProfileDTO(
            telegram_id=user.telegram_id,
            purchases_count=orders_count,
            stars_bought=total_stars,
        )

    async def get_active_promo(self, telegram_id: int) -> PromoCode | None:
        user = await self.get_by_telegram_id(telegram_id, is_select_promo=True)
        if user is not None:
            return user.active_promo

        return None

    @staticmethod
    async def update_active_promo(user: TelegramUser, promo: PromoCode | None) -> TelegramUser:
        user.active_promo = promo

        if promo is None:
            user.promo_since = None
        else:
            user.promo_since = Now()

        await user.asave(update_fields=["active_promo", "promo_since"])
        return user

    @staticmethod
    async def update_username(user: TelegramUser, new_username: str) -> TelegramUser:
        """Обновляет юзернейм существующего пользователя."""
        user.username = new_username.lstrip("@")
        await user.asave(update_fields=["username", "updated_at"])
        return user

    @staticmethod
    async def delete_active_promo(user: TelegramUser) -> TelegramUser:
        user.active_promo = None
        user.promo_since = None
        await user.asave(update_fields=["active_promo", "promo_since"])
        return user

    @staticmethod
    async def delete_user(user: TelegramUser) -> None:
        _ = await user.adelete()
