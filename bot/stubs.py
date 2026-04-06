from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UserProfileDTO:
    telegram_id: int
    purchases_count: int
    stars_bought: int
    balance: float
    ref_link: str


class SupportService:
    async def get_support_url(self) -> str:
        return "https://t.me/support_agent"


class TelegramApiService:
    async def resolve_username(self, username: str) -> bool:
        """Проверяет, существует ли пользователь в Telegram."""
        return True


class StatsService:
    async def get_order_history(self, user_id: int, page: int) -> List[dict]:
        return [{"date": "12.03.2026", "stars": 50, "price": 69}]

    async def get_referrals(self, user_id: int, page: int) -> dict:
        return {"total_invited": 1, "earned": 13.5, "items": [{"id": 123, "username": "@dween", "earned": 13.5}]}

    async def get_referral_purchases(self, ref_user_id: int, page: int) -> List[dict]:
        return [{"date": "12.03.2026", "stars": 50, "price": 3.45}]
