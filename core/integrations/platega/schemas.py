from typing import TypedDict
from collections.abc import Mapping


class PlategaAPIError(Exception):
    """Базовая ошибка при работе с API Platega."""


class PaymentPayloadDict(TypedDict):
    user_id: int
    message_id: int
    price: float
    stars_count: int
    target_username: str


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
