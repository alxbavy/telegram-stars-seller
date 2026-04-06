from datetime import datetime

from core.models import TelegramUser


class UserRepository:
    @staticmethod
    async def create_telegram_user(telegram_id: int, username: str) -> TelegramUser:
        return await TelegramUser.objects.acreate(telegram_id=telegram_id, username=username)

    @staticmethod
    async def get_by_telegram_id(telegram_id: int) -> TelegramUser | None:
        return await TelegramUser.objects.filter(telegram_id=telegram_id).afirst()

    @staticmethod
    async def get_by_username(username: str) -> TelegramUser | None:
        clean_username = username.lstrip("@")
        return await TelegramUser.objects.filter(username=clean_username).afirst()

    @staticmethod
    async def get_many_by_date_period(start_date: datetime, end_date: datetime) -> list[TelegramUser]:
        """Возвращает список пользователей, зарегистрированных в указанный период (включительно)."""
        return [
            user async for user in TelegramUser.objects.filter(created_at__range=(start_date, end_date))
        ]

    @staticmethod
    async def update_username(user: TelegramUser, new_username: str) -> TelegramUser:
        """Обновляет юзернейм существующего пользователя."""
        user.username = new_username.lstrip("@")
        await user.asave(update_fields=["username"])
        return user

    @staticmethod
    async def delete_user(user: TelegramUser) -> None:
        await user.adelete()
