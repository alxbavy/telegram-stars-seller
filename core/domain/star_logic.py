from decimal import Decimal, ROUND_HALF_UP


def calculate_variable_price(
    base_star_price: Decimal,
    current_usd_rate: Decimal,
    base_usd_rate: Decimal,
    is_use_usd_rate: bool
) -> Decimal:
    """Вычисляет цену звезды по формуле коррекции курса."""
    if is_use_usd_rate:
        rate_factor = current_usd_rate / base_usd_rate
        return base_star_price * rate_factor
    
    return base_star_price

def apply_commission(amount: Decimal, commission_percent: Decimal) -> Decimal:
    """Применяет комиссию платежной системы."""
    factor = (Decimal("100") + commission_percent) / Decimal("100")
    return (amount * factor).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)

def final_stars_cost(stars_count: int, price_per_star: Decimal) -> Decimal:
    """Итоговая стоимость звезд до применения комиссий эквайринга."""
    return (Decimal(stars_count) * price_per_star).quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
