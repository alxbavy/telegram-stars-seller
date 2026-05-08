from decimal import Decimal

from core.dto.payment import PricingDTO
from core.models import GlobalSettings, ExchangeRate, PaymentMethod


class PaymentRepository:
    model_settings = GlobalSettings
    model_exchange_rate = ExchangeRate
    model_payment_method = PaymentMethod

    async def get_pricing_data(self) -> PricingDTO:
        """Объединение двух SQL-запросов в один поток для производительности."""
        return PricingDTO(
            settings=await self.model_settings.aget_solo(),
            exchange_rate=await self.model_exchange_rate.aget_solo()
        )

    async def get_payment_method_by_name(
            self,
            payment_method: str,
            is_check_is_active: bool = True,
            is_active_value: bool = True
    ) -> PaymentMethod | None:
        query = self.model_payment_method.objects.filter(name=payment_method)
        if is_check_is_active:
            query = query.filter(is_active=is_active_value)
        return await query.afirst()

    async def get_many_by(
            self,
            is_check_is_active: bool = True,
            is_active_value: bool = True
    ) -> list[PaymentMethod]:
        """Возвращает активные методы оплаты для отображения в боте."""
        query = self.model_payment_method.objects
        if is_check_is_active:
            query = query.filter(is_active=is_active_value)
        return [method async for method in query.all()]

    async def update_current_usd_rate(self, current_usd_rate: Decimal) -> None:
        """Метод для сохранения текущего курса доллара при его обновлении по таймеру."""
        exchange_rate = await self.model_exchange_rate.aget_solo()
        exchange_rate.usd_rate = current_usd_rate
        await exchange_rate.asave(update_fields=["usd_rate", "updated_at"])

    async def is_maintenance_mode(self) -> bool:
        settings = await self.model_settings.aget_solo()
        return settings.maintenance_mode
