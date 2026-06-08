import asyncio
from collections.abc import Mapping
from decimal import Decimal
from uuid import UUID

import httpx
import re
import logging
from urllib.parse import urljoin
from typing import cast, final

from django.conf import settings

from core.dto.payment import PaymentDTO
from core.integrations.platega.schemas import PlategaAPIError, TransactionCreationResponse


logger = logging.getLogger(__name__)


@final
class PlategaClient:
    PAYMENT_WITH_METHOD_PATH = "transaction/process"

    def __init__(self) -> None:
        self.url = cast(str, getattr(settings, "PLATEGA_API_URL", None))
        self.merchant_id = cast(str, getattr(settings, "PLATEGA_MERCHANT_ID", None))
        self.secret = cast(str, getattr(settings, "PLATEGA_SECRET", None))

        if not all([self.url, self.merchant_id, self.secret]):
            logger.error("PlategaClient не сконфигурирован.")
            raise ValueError("PlategaClient is not configured properly")

        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def create_payment(
            self,
            payment_method: int,
            amount: float,
            currency: str,
            description: str,
            payload: str = ""
    ) -> PaymentDTO:
        # Заглушка для тестов
        # import uuid
        # return PaymentDTO(
        #     transaction_id=uuid.uuid4(),
        #     pay_url="https://test.link",
        #     price=Decimal(amount),
        #     expires_in="00:30:00"
        # )

        description_pattern = re.compile(r"^TgId:\d+\nUserId:\d+$")
        if not description_pattern.search(description):
            raise ValueError("Platega payment description is invalid")

        method = "POST"
        data = {
            "paymentMethod": str(payment_method),
            "paymentDetails": {
                "amount": str(amount),
                "currency": currency,
            },
            "description": description,
        }
        if payload:
            data["payload"] = payload

        await asyncio.sleep(2)
        response = await self._make_request(method, self.PAYMENT_WITH_METHOD_PATH, data)

        if response.status_code == 200:
            data = cast(TransactionCreationResponse, response.json())

            if isinstance(data["paymentDetails"], dict):
                price = str(data["paymentDetails"]["amount"])
            else:
                price_pattern = re.compile(r"^(\S+)")
                price = price_pattern.match(data["paymentDetails"]).group()

            return PaymentDTO(
                transaction_id=UUID(data["transactionId"]),
                pay_url=data["redirect"],
                price=Decimal(price),
                expires_in=data["expiresIn"]
            )

        if response.status_code == 400:
            logger.exception("Ошибка валидации во время создания платежа на Platega")
            raise PlategaAPIError(f"Ошибка валидации во время создания платежа:\n{data = }")

        if response.status_code == 401:
            logger.exception("Не удалось авторизоваться во время создания платежа на Platega")
            raise PlategaAPIError("Не удалось авторизоваться во время создания платежа")

        logger.exception("Неизвестная ошибка во время создания платежа на Platega")
        raise PlategaAPIError(f"Неизвестная ошибка во время создания платежа:\n{data = }\n{response = }")

    async def _make_request(self, method: str, path: str, data: Mapping[str, object] | None = None) -> httpx.Response:
        headers = self._get_headers(method)
        full_url = urljoin(self.url, path)

        try:
            if method == "POST":
                response = await self._client.post(full_url, json=data, headers=headers, timeout=30.0)
            else:
                response = await self._client.get(full_url, headers=headers, timeout=30.0)

        except httpx.TimeoutException as exc:
            logger.exception(f"Превышено время ожидания при попытке создать платёж на Platega")
            raise PlategaAPIError("Превышено время ожидания при попытке создать платёж") from exc

        except httpx.HTTPError as exc:
            logger.exception(f"Ошибка HTTP во время создания платежа на Platega: {exc}")
            raise PlategaAPIError(f"Ошибка HTTP во время создания платежа: {exc}") from exc

        return response

    def _get_headers(self, method: str, path: str = ""):
        if path:
            raise NotImplementedError("headers for concrete path is not supported now")

        if method == "POST":
            return {
                "X-MerchantId": self.merchant_id,
                "X-Secret": self.secret,
                "Content-Type": "application/json",
            }
        elif method == "GET":
            return {
                "X-MerchantId": self.merchant_id,
                "X-Secret": self.secret,
            }
        else:
            raise ValueError(f"Invalid method for headers: {method}")
