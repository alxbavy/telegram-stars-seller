from typing import final
from core.dto.user import UserProfileDTO
from core.repositories.user import UserRepository
from core.models import TelegramUser, PromoCode


class UnregisteredUser(Exception):
    def __init__(self, user_id: int, message: str | None = None):
        if message is None:
            message = f"User with id {user_id} was not registered"
        self.message = message

        super().__init__(self.message)


@final
class UserService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def register_user(self, telegram_id: int, username: str | None) -> TelegramUser:
        user = await self._user_repo.get_by_telegram_id(telegram_id)

        safe_username = username or ""

        if not user:
            user = await self._user_repo.create_telegram_user(
                telegram_id=telegram_id,
                username=safe_username
            )

        else:
            if safe_username and user.username != safe_username.lstrip("@"):
                user = await self._user_repo.update_username(user, safe_username)

        return user

    async def update_active_promo(self, telegram_id: int, promo: PromoCode | None) -> TelegramUser:
        user = await self._user_repo.get_by_telegram_id(telegram_id)
        if user is None:
            raise UnregisteredUser(telegram_id)

        return await self._user_repo.update_active_promo(user, promo)

    async def get_profile_data(self, user_id: int) -> UserProfileDTO:
        profile_data = await self._user_repo.get_user_stats(user_id)

        if profile_data is None:
            raise UnregisteredUser(user_id)

        return profile_data

    async def get_users_with_promo_id_count(self, promo_id: int) -> int:
        return await self._user_repo.get_many_by(
            is_count_only=True,
            is_select_promo=True, promo_id=promo_id,
        )
