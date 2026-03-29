from core.repositories.user_repository import UserRepository
from core.repositories.trans_repo import TransactionRepository

class UserService:
    def __init__(self, user_repo: UserRepository, trans_repo: TransactionRepository):
        self._user_repo = user_repo
        self._trans_repo = trans_repo

    async def get_profile_data(self, user_id: int) -> UserProfileDTO | None:
        user = await self._user_repo.get_by_telegram_id(user_id)

        # TODO: порядок действий, если юзер не зарегистрирован? пока return None
        if not user:
            return None

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