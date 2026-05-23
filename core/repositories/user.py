from datetime import datetime

from django.db.models import Sum

from core.domain.enums import TransactionStatus
from core.dto.user import UserProfileDTO
from core.models import TelegramUser


class UserRepository:
    model: type[TelegramUser] = TelegramUser

    async def create_telegram_user(self, telegram_id: int, username: str) -> TelegramUser:
        return await self.model.objects.acreate(telegram_id=telegram_id, username=username)

    async def get_by_telegram_id(self, telegram_id: int, is_prefetch_transactions: bool = False) -> TelegramUser | None:
        query = self.model.objects.filter(telegram_id=telegram_id)
        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")
        return await query.afirst()

    async def get_by_username(self, username: str, is_prefetch_transactions: bool = False) -> TelegramUser | None:
        clean_username = username.lstrip("@")
        query = self.model.objects.filter(username=clean_username)
        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")
        return await query.afirst()

    async def get_many_by_date_period(
            self,
            start_date: datetime,
            end_date: datetime,
            is_prefetch_transactions: bool = False
    ) -> list[TelegramUser]:
        """Возвращает список пользователей, зарегистрированных в указанный период (включительно)."""
        query = self.model.objects.filter(created_at__range=(start_date, end_date))
        if is_prefetch_transactions:
            query = query.prefetch_related("transactions")
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

    @staticmethod
    async def update_username(user: TelegramUser, new_username: str) -> TelegramUser:
        """Обновляет юзернейм существующего пользователя."""
        user.username = new_username.lstrip("@")
        await user.asave(update_fields=["username"])
        return user

    @staticmethod
    async def delete_user(user: TelegramUser) -> None:
        _ = await user.adelete()
