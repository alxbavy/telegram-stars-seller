from decimal import Decimal
from typing import overload

from dishka import FromDishka

from core.dto.payment import PaymentMethodDTO
from core.repositories.utils import db_action_with_tenacity
from core.services.payment import PaymentService
from core.services.star_price import StarService
from core.ioc import inject
from core.models import PromoCode


@overload
async def get_payment_methods_with_prices(  # noqa  # pyright: ignore[reportInconsistentOverload]
        active_promo: PromoCode | None,
        stars_count: int
) -> list[tuple[PaymentMethodDTO, Decimal]]: ...


@inject
async def get_payment_methods_with_prices(
        active_promo: PromoCode | None,
        stars_count: int,
        *,
        payment_service: FromDishka[PaymentService],
        star_service: FromDishka[StarService]
) -> list[tuple[PaymentMethodDTO, Decimal]]:
    discount: Decimal = 1 - (active_promo.discount / 100) if active_promo is not None else Decimal("1.00")
    return [
        (
            payment_method,
            round(
                number=await db_action_with_tenacity(
                    star_service.get_order_price, stars_count, payment_method
                ) * discount,
                ndigits=2
            )
        ) for payment_method in await db_action_with_tenacity(payment_service.get_active_payment_methods)
    ]
