from decimal import Decimal
from core.repositories.payment import PaymentRepository
from core.domain import star_logic


class StarService:
    def __init__(self, payment_repo: PaymentRepository):
        self._payment_repo = payment_repo

    async def get_order_price(self, stars_count: int, payment_method: str) -> Decimal:
        """Возвращает финальную стоимость заказа со всеми комиссиями."""
        settings, exchange_rate = await self._payment_repo.get_pricing_data()

        price_per_star = star_logic.calculate_variable_price(
            base_star_price=settings.star_base_cost,
            current_usd_rate=exchange_rate.usd_rate,
            base_usd_rate=settings.usd_base_rate,
            is_use_usd_rate=settings.is_use_usd_rate
        )
        stars_total_price_raw = star_logic.final_stars_cost(stars_count, price_per_star)

        payment_method_obj = await self._payment_repo.get_payment_method_by_name(payment_method)
        stars_total_price_final = star_logic.apply_commission(
            stars_total_price_raw, payment_method_obj.commission_percent
        )

        return stars_total_price_final
