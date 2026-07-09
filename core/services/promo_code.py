from typing import final

from core.repositories.promo_code import PromoCodeRepository
from core.repositories.user import UserRepository
from core.models import PromoCode


@final
class PromoCodeService:
    def __init__(self, promo_repo: PromoCodeRepository, user_repo: UserRepository):
        self._promo_repo = promo_repo
        self._user_repo = user_repo

    async def get_promo_by_name(self, name: str | None) -> PromoCode | None:
        if name is None:
            return None

        return await self._promo_repo.get_promo_by_name(name, is_use_is_active=False)

    async def get_active_promo_for_telegram_user_id(self, telegram_user_id: int) -> PromoCode | None:
        return await self._user_repo.get_active_promo(telegram_user_id)
