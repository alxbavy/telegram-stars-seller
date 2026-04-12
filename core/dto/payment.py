from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple

from core.models import GlobalSettings, ExchangeRate


@dataclass(frozen=True)
class PaymentDTO:
    transaction_id: int
    pay_url: str
    amount: Decimal


class PricingDTO(NamedTuple):
    settings: GlobalSettings
    exchange_rate: ExchangeRate