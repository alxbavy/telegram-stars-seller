from core.dto.user import UserProfileDTO
from core.repositories.transaction import TransactionRepository
from core.repositories.user import UserRepository


class UnregisteredUser(Exception):
    def __init__(self, user_id: int, message: str | None = None):
        if message is None:
            message = f"User with id {user_id} was not registered"
        self.message = message

        super().__init__(self.message)


class UserService:
    def __init__(self, user_repo: UserRepository, trans_repo: TransactionRepository):
        self._user_repo = user_repo
        self._trans_repo = trans_repo

    async def register_user(self, telegram_id: int, username: str | None):
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

    async def get_profile_data(self, user_id: int) -> UserProfileDTO:
        user = await self._user_repo.get_by_telegram_id(user_id)

        if not user:
            raise UnregisteredUser(user_id)

        stats = await self._trans_repo.get_user_stats(user)
        return UserProfileDTO(
            user.telegram_id,
            stats['total_stars'],
            stats['orders_count'],
        )
