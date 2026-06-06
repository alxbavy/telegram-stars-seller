from typing import TypedDict, NotRequired
from collections.abc import Mapping


class PlategaAPIError(Exception):
    """Базовая ошибка при работе с API Platega."""


class PaymentPayloadDict(TypedDict):
    user_id: int
    message_id: int
    stars_count: int
    target_username: NotRequired[str]


class TransactionCreationResponse(TypedDict):
    transactionId: str
    redirect: str
    paymentDetails: str | dict[str, int | str]
    expiresIn: str


type PlategaHeaders = Mapping[str, object]


class PlategaRequestJson(TypedDict):
    id: str
    amount: float
    currency: str
    status: str
    paymentMethod: int
    payload: str
