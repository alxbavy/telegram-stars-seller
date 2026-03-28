from typing import Any
from urllib.parse import urljoin

import httpx
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


class FragmentAPIError(Exception):
    """Базовая ошибка клиента Fragment API."""


class FragmentClient:
    AUTH_PATH = "auth/authenticate/"
    SEND_STARS_PATH = "order/stars/"

    def __init__(self):
        self.url: str | None = getattr(settings, "FRAGMENT_API_URL", None)
        self.api_key: str | None = getattr(settings, "FRAGMENT_API_KEY", None)
        self.mnemonics: str | None = getattr(settings, "FRAGMENT_MNEMONICS", None)
        self.phone: str | None = getattr(settings, "FRAGMENT_PHONE", None)
        self.wallet_version: str | None = getattr(settings, "TON_WALLET_VERSION", None)

        if not all([self.url, self.api_key, self.mnemonics, self.phone, self.wallet_version]):
            logger.error("FragmentAPI не сконфигурирован.")
            raise ValueError("FragmentAPI is not configured properly")

        self.token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send_stars(self, username: str, amount_stars: int) -> dict[str, Any]:
        if not username or not username.strip():
            raise ValueError("username must not be empty")
        if amount_stars <= 0:
            raise ValueError("amount_stars must be positive")

        await self._ensure_authenticated()

        payload = {
            "username": username,
            "quantity": amount_stars,
            "show_sender": False
        }

        return await self._send_stars_request(payload)

    async def _send_stars_request(self, payload: dict[str, Any], retry_on_401: bool=True) -> dict[str, Any]:
        headers = {
            "Authorization": f"JWT {self.token}",
            "Content-Type": "application/json"
        }

        try:
            response = await self._client.post(
                urljoin(self.url, self.SEND_STARS_PATH),
                json=payload,
                headers=headers,
                timeout=30.0
            )
        except httpx.TimeoutException as exc:
            raise FragmentAPIError("Timeout while sending stars") from exc
        except httpx.HTTPError as exc:
            raise FragmentAPIError(f"HTTP error while sending stars: {exc}") from exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 401 and retry_on_401:
            logger.debug("Токен Fragment истек, обновляем и пробуем снова...")
            self.token = None
            await self._ensure_authenticated()
            return await self._send_stars_request(payload, retry_on_401=False)

        logger.error(f"Не удалось отправить звёзды: {response.text}")
        raise FragmentAPIError(
            f"Failed to send stars: status={response.status_code}, body={response.text}"
        )

    async def _ensure_authenticated(self) -> None:
        if self.token:
            return

        await self._authenticate_fragment()

        if not self.token:
            raise FragmentAPIError("Authentication failed")

    async def _authenticate_fragment(self) -> None:
        if not self.mnemonics:
            logger.error("Аутентификация невозможна: отсутствуют мнемоники.")
            raise FragmentAPIError("Mnemonics are missing")

        payload = {
            "api_key": self.api_key,
            "phone_number": self.phone,
            "mnemonics": self.mnemonics.strip().split(),
            "version": self.wallet_version
        }

        try:
            response = await self._client.post(
                urljoin(self.url, self.AUTH_PATH),
                json=payload,
                timeout=15.0
            )
        except httpx.TimeoutException as exc:
            logger.exception("Исключение при авторизации Fragment")
            raise FragmentAPIError("Timeout during authentication") from exc
        except httpx.HTTPError as exc:
            logger.exception("Исключение при авторизации Fragment")
            raise FragmentAPIError(f"HTTP error during authentication: {exc}") from exc

        if response.status_code != 200:
            logger.error(f"Ошибка авторизации Fragment: {response.status_code} - {response.text}")
            raise FragmentAPIError(
                f"Authentication failed: status={response.status_code}, body={response.text}"
            )

        token = response.json().get("token")
        if not token:
            raise FragmentAPIError("Authentication succeeded but token is missing")

        self.token = token
        logger.debug("Успешная авторизация во Fragment API.")
