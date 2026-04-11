from decimal import Decimal

from core.models import GlobalSettings, ExchangeRate, PaymentMethod
from core.schemas.payment import PricingDTO


class PaymentRepository:
    @staticmethod
    async def get_pricing_data() -> PricingDTO:
        """Объединение двух SQL-запросов в один поток для производительности."""
        return PricingDTO(
            settings=await GlobalSettings.aget_solo(),
            exchange_rate=await ExchangeRate.aget_solo()
        )

    @staticmethod
    async def get_payment_method_by_name(payment_method: str) -> PaymentMethod | None:
        """Если переданного метода нет, или он неактивен, то вернётся None."""
        return await PaymentMethod.objects.filter(name=payment_method, is_active=True).afirst()

    @staticmethod
    async def get_all_active_methods() -> list[PaymentMethod]:
        """Возвращает активные методы оплаты для отображения в боте."""
        return [
            method async for method in PaymentMethod.objects.filter(is_active=True)
        ]

    @staticmethod
    async def update_current_usd_rate(current_usd_rate: Decimal) -> None:
        """Метод для сохранения текущего курса доллара при его обновлении по таймеру."""
        exchange_rate = await ExchangeRate.aget_solo()
        exchange_rate.usd_rate = current_usd_rate
        await exchange_rate.asave(update_fields=["usd_rate", "updated_at"])

    @staticmethod
    async def is_maintenance_mode() -> bool:
        settings = await GlobalSettings.aget_solo()
        return settings.maintenance_mode
