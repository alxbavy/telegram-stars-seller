from decimal import Decimal

from asgiref.sync import sync_to_async

from core.models import GlobalSettings, ExchangeRate, PaymentMethod
from core.schemas.payment import PricingDTO


class PaymentRepository:
    @sync_to_async(thread_sensitive=True)
    def get_pricing_data(self) -> PricingDTO:
        """Объединение двух SQL-запросов в один поток для производительности."""
        return PricingDTO(
            settings=GlobalSettings.get_solo(),
            exchange_rate=ExchangeRate.get_solo()
        )

    @sync_to_async(thread_sensitive=True)
    def get_payment_method_by_name(self, payment_method: str) -> PaymentMethod | None:
        """Если переданного метода нет, или он неактивен, то вернётся None."""
        return PaymentMethod.objects.filter(name=payment_method, is_active=True).first()

    @sync_to_async(thread_sensitive=True)
    def get_all_active_methods(self) -> list[PaymentMethod]:
        """Возвращает активные методы оплаты для отображения в боте."""
        return list(PaymentMethod.objects.filter(is_active=True))

    @sync_to_async(thread_sensitive=True)
    def update_current_usd_rate(self, current_usd_rate: Decimal) -> None:
        """Метод для сохранения текущего курса доллара при его обновлении по таймеру."""
        exchange_rate = ExchangeRate.get_solo()
        exchange_rate.usd_rate = current_usd_rate
        exchange_rate.save(update_fields=["usd_rate", "updated_at"])

    @sync_to_async(thread_sensitive=True)
    def is_maintenance_mode(self) -> bool:
        return GlobalSettings.get_solo().maintenance_mode
