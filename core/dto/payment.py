from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from core.models import GlobalSettings, ExchangeRate


@dataclass(frozen=True)
class PaymentDTO:
    transaction_id: UUID
    pay_url: str
    price: Decimal
    expires_in: str


@dataclass(frozen=True)
class PricingDTO:
    settings: GlobalSettings
    exchange_rate: ExchangeRate
