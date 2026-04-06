from datetime import datetime

from asgiref.sync import sync_to_async

from core.models import TelegramUser


class UserRepository:
    @sync_to_async(thread_sensitive=True)
    def create_telegram_user(self, telegram_id: int, username: str) -> TelegramUser:
        clean_username = username.lstrip("@")
        return TelegramUser.objects.create(telegram_id=telegram_id, username=clean_username)

    @sync_to_async(thread_sensitive=True)
    def get_by_telegram_id(self, telegram_id: int) -> TelegramUser | None:
        return TelegramUser.objects.filter(telegram_id=telegram_id).first()

    @sync_to_async(thread_sensitive=True)
    def get_by_username(self, username: str) -> TelegramUser | None:
        clean_username = username.lstrip("@")
        return TelegramUser.objects.filter(username=clean_username).first()

    @sync_to_async(thread_sensitive=True)
    def get_many_by_date_period(self, start_date: datetime, end_date: datetime) -> list[TelegramUser]:
        """Возвращает список пользователей, зарегистрированных в указанный период (включительно)."""
        qs = TelegramUser.objects.filter(created_at__range=(start_date, end_date))
        return list(qs)

    @sync_to_async(thread_sensitive=True)
    def update_username(self, user: TelegramUser, new_username: str) -> TelegramUser:
        """Обновляет юзернейм существующего пользователя."""
        user.username = new_username.lstrip("@")
        user.save(update_fields=["username"])
        return user

    @sync_to_async(thread_sensitive=True)
    def delete_user(self, user: TelegramUser) -> None:
        user.delete()
