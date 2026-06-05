from typing import Annotated, TypedDict, NotRequired, Protocol
from datetime import datetime
from decimal import Decimal
from uuid import UUID


class HasCurrency(TypedDict):
    currency: str


class HasPrice(TypedDict):
    price: Annotated[str, Decimal]


class HasUpdatedAt(TypedDict):
    updated_at: Annotated[str, datetime]


class HasAmount(TypedDict):
    amount: Annotated[str, Decimal]


class StarsJSON(HasCurrency, HasPrice, HasUpdatedAt):
    quantity: int


class PremiumJSON(HasCurrency, HasPrice, HasUpdatedAt):
    months: int


class CurrentPricesResponse(TypedDict):
    stars: tuple[StarsJSON, ...] | None
    premium: tuple[PremiumJSON, ...] | None


class BalanceForCurrencyJSON(HasCurrency, HasAmount): pass


class BalanceResponse(TypedDict):
    balances: tuple[BalanceForCurrencyJSON, ...]


class Sender(TypedDict):
    phone_number: str
    name: NotRequired[str | None]


class StarsPrice(HasCurrency, HasAmount): pass
class StarsFee(HasCurrency, HasAmount): pass


class SendStarsResponse(TypedDict):
    success: bool | None
    id: NotRequired[Annotated[str, UUID]]
    receiver: str
    goods_quantity: NotRequired[int | None]
    sender: Sender | None
    price: StarsPrice | None
    fee: StarsFee | None
    ref_id: str | None
    status: str
    type: str
    error: object
    created_at: Annotated[str, datetime]
    bot_warning: NotRequired[str]
