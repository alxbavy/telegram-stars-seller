from typing import TypedDict
from collections.abc import Mapping


class PlategaAPIError(Exception):
    """Базовая ошибка при работе с API Platega."""


class PaymentRequestDetailsJson(TypedDict):
    amount: float
    currency: str


class PaymentPayloadDict(TypedDict):
    user_id: int
    message_id: int
    price: float
    stars_count: int
    target_username: str


class PaymentRequestJson(TypedDict):
    paymentMethod: int
    paymentDetails: PaymentRequestDetailsJson
    description: str
    payload: str


class TransactionCreationResponse(TypedDict):
    transactionId: str
    redirect: str
    paymentDetails: str | dict[str, int | str]
    expiresIn: str


type PlategaHeaders = Mapping[str, object]


class PlategaWebhookRequestJson(TypedDict):
    id: str
    amount: float
    currency: str
    status: str
    paymentMethod: int
    payload: str
