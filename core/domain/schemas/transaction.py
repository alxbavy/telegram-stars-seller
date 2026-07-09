from uuid import UUID
from decimal import Decimal
from typing import TypedDict, NotRequired

from core.domain.enums import TransactionStatus
from core.models import TelegramUser, Transaction


class TransactionKwargs(TypedDict):
    id: UUID
    telegram_user: TelegramUser
    amount_fiat: float
    amount_stars: int
    target_username: NotRequired[str]
    status: TransactionStatus
    message_id: NotRequired[int]
    pay_url: str


class TransactionMetaKwargs(TypedDict):
    transaction: Transaction
    type: str
    payment_method: str
    promo_id: NotRequired[int]
    promo_name: NotRequired[str]
    promo_discount: NotRequired[Decimal]
    payload: dict[str, object]
