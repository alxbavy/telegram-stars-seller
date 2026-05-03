from decimal import Decimal
from core.domain import star_logic
from core.repositories.payment import PaymentRepository


class StarService:
    STAR_PRICES_RUB = {
        50: Decimal("75"),
        100: Decimal("113"),
        150: Decimal("225"),
        250: Decimal("375"),
        350: Decimal("525"),
        500: Decimal("750"),
        750: Decimal("1125"),
        1000: Decimal("1500"),
        1500: Decimal("2250"),
        2500: Decimal("3750"),
        5000: Decimal("7500"),
        10000: Decimal("15000"),
    }

    def __init__(self, payment_repo: PaymentRepository):
        self._payment_repo = payment_repo

    async def get_order_price(self, stars_count: int, payment_method: str) -> Decimal:
        """Возвращает финальную стоимость заказа в рублях со всеми комиссиями."""

        stars_total_price_raw = self.STAR_PRICES_RUB.get(stars_count)

        if stars_total_price_raw is None:
            price_per_one = self.STAR_PRICES_RUB[10000] / 10000
            stars_total_price_raw = stars_count * price_per_one

        return stars_total_price_raw
