from decimal import Decimal
from typing import Annotated, TypedDict, NotRequired, final


class FragmentAPIError(Exception):
    """Базовая ошибка клиента Fragment API."""


@final
class FragmentAPITooManyRequests(Exception):
    """Ошибка для HTTP со статусом 429."""
    def __init__(self, retry_after: int | float | None = None, message: str | None = None) -> None:
        self.retry_after = retry_after
        self.message = message
        super().__init__(self.message)


class StarsJSON(TypedDict):
    quantity: int
    price: str
    currency: str
    updated_at: str


class PremiumJSON(TypedDict):
    months: int
    price: str
    currency: str
    updated_at: str


class CurrentPricesResponse(TypedDict):
    stars: tuple[StarsJSON] | None
    premium: tuple[PremiumJSON] | None


class BalanceForCurrencyJSON(TypedDict):
    currency: str
    amount: Annotated[str, Decimal]


class BalanceResponse(TypedDict):
    balances: tuple[BalanceForCurrencyJSON]


class Sender(TypedDict):
    phone_number: str
    name: NotRequired[str | None]


class SendStarsResponse(TypedDict):
    success: bool | None
    id: NotRequired[str]
    receiver: str
    goods_quantity: NotRequired[int | None]
    sender: Sender | None
    ton_price: str | None
    fee_ton: str | None
    ref_id: str | None
    status: str
    type: str
    error: object
    created_at: str
