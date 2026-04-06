from core.repositories.user_repository import UserRepository
from core.repositories.trans_repo import TransactionRepository


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

    async def get_profile_data(self, user_id: int) -> UserProfileDTO | None:
        user = await self._user_repo.get_by_telegram_id(user_id)

        if not user:
            raise UnregisteredUser(user_id)

        stats = await self._trans_repo.get_user_stats(user)
        return UserProfileDTO({
            "user": user,
            "total_stars": stats['total_stars'],
            "orders_count": stats['orders_count'],
        })

        # {
        #     "user": user,
        #     "total_stars": stats['total_stars'],
        #     "orders_count": stats['orders_count']
        # }