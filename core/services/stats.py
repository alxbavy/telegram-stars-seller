class StatsService:
    async def get_order_history(self, user_id: int, page: int) -> list[dict]:
        return [{"date": "12.03.2026", "stars": 50, "price": 69}]

    async def get_referrals(self, user_id: int, page: int) -> dict:
        return {"total_invited": 1, "earned": 13.5, "items": [{"id": 123, "username": "@dween", "earned": 13.5}]}

    async def get_referral_purchases(self, ref_user_id: int, page: int) -> list[dict]:
        return [{"date": "12.03.2026", "stars": 50, "price": 3.45}]
