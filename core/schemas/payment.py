from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class PaymentDTO:
    transaction_id: int
    pay_url: str
    amount: Decimal
