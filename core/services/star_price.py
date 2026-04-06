from decimal import Decimal
from core.domain import star_logic


class StarService:
    '''def __init__(self, settings_repo):
        self.settings_repo = settings_repo'''

    async def get_order_price(self, stars_count: int, payment_method: str) -> Decimal:
        """Возвращает финальную стоимость заказа со всеми комиссиями."""
        settings = self.settings_repo.get_active_settings()

        if settings.is_auto_update:
            price_per_star = star_logic.calculate_variable_price(
                base_star_price=Decimal(str(settings.base_star_price)),
                current_usd_rate=Decimal(str(settings.current_usd_rate)),
                base_usd_rate=Decimal(str(settings.base_usd_rate))
            )
        else:
            price_per_star = Decimal(str(settings.base_star_price))

        raw_amount = star_logic.final_stars_cost(stars_count, price_per_star)

        comm_pct = settings.sbp_commission if payment_method == "sbp" else settings.card_commission

        final_amount = star_logic.apply_commission(raw_amount, Decimal(str(comm_pct)))

        return final_amount