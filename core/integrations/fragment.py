import asyncio
from typing import final, cast
from urllib.parse import urljoin

import httpx
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


class FragmentAPIError(Exception):
    """Базовая ошибка клиента Fragment API."""


@final
class FragmentClient:
    AUTH_PATH = "auth/authenticate/"
    SEND_STARS_PATH = "order/stars/"
    GET_USER_PATH = "misc/user/"

    def __init__(self):
        self.url = cast(str, getattr(settings, "FRAGMENT_API_URL", None))
        self.api_key = cast(str, getattr(settings, "FRAGMENT_API_KEY", None))
        self.mnemonics = cast(str, getattr(settings, "FRAGMENT_MNEMONICS", None))
        self.phone = cast(str, getattr(settings, "FRAGMENT_PHONE", None))
        self.wallet_version = cast(str, getattr(settings, "TON_WALLET_VERSION", None))

        if not all([self.url, self.api_key, self.mnemonics, self.phone, self.wallet_version]):
            logger.error("FragmentAPI не сконфигурирован.")
            raise ValueError("FragmentAPI is not configured properly")

        self.token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def resolve_username(self, username: str) -> bool:
        """
        Принимает `username`. Наличие знака `@` неважно. `username` должен начинаться с любой буквы, далее разрешены
        любые буквы, цифры и знак `_`. Длина `username` (без учёта `@`) - от `2` до `31` знаков.

        Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::

            Некорректный `username`
            Таймауты
            HTTPError
            Ошибки аутентификации
            Неизвестные ошибки от fragment-api

        Returns:
            если пользователь найден - `True`, иначе `False`
        """
        if username == "True":  # TODO: для дебага - убрать в релизе
            return True
        else:
            return False
        username = username.lstrip("@")
        return await self._find_user_by_username(username)

    async def send_stars(self, username: str, amount_stars: int) -> dict[str, object]:
        """
        Принимает `username` и `amount_stars`.

        `amount_stars` в текущем виде проверяются во фронте.

        `username` проверяется во fragment-api, поэтому в случае некорректного username будет ошибка 400.

        Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::

            Некорректный `username`
            Таймауты
            HTTPError
            Ошибки аутентификации
            Неизвестные ошибки от fragment-api

        Ошибки `FragmentAPIError` следует отлавливать для отображения информации об ошибках пользователю.
        """

        if not username or not username.strip():
            raise ValueError("username must not be empty")
        if amount_stars <= 0:
            raise ValueError("amount_stars must be positive")

        if not await self.resolve_username(username):
            pass # TODO: реализовать поведение при отсутствии username

        payload = {
            "username": username,
            "quantity": amount_stars,
            "show_sender": False
        }

        return await self._send_stars_request(payload)

    async def _find_user_by_username(self, username: str) -> bool:
        """
        Принимает username без знака `@`.

        Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::

            Некорректный `username`
            Таймауты
            HTTPError
            Ошибки аутентификации
            Неизвестные ошибки от fragment-api

        Returns:
            если пользователь найден - `True`, иначе `False`
        """
        await self._ensure_authenticated()

        headers = await self._get_headers("GET")

        await asyncio.sleep(2)
        try:
            response = await self._client.get(
                urljoin(self.url, f"{self.GET_USER_PATH}{username}/"),
                headers=headers,
                timeout=30.0
            )
        except httpx.TimeoutException as e:
            raise FragmentAPIError("Превышено время ожидания от fragment-api при проверке username") from e
        except httpx.HTTPError as e:
            raise FragmentAPIError(f"Ошибка HTTP от fragment-api при проверке username: {e}") from e

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        if response.status_code == 400:
            raise FragmentAPIError(f"Произошла неизвестная ошибка со стороны fragment-api:\n{response.json()}")

        raise FragmentAPIError(
            f"Неизвестный ответ от сервера fragment-api:\n{response.status_code = } - {response.text = }"
        )

    async def _send_stars_request(
            self,
            payload: dict[str, str | int | bool],
            retry_on_401: bool=True
    ) -> dict[str, object]:
        await self._ensure_authenticated()

        headers = await self._get_headers("POST")

        try:
            response = await self._client.post(
                urljoin(self.url, self.SEND_STARS_PATH),
                json=payload,
                headers=headers,
                timeout=30.0
            )
        except httpx.TimeoutException as exc:
            logger.exception(f"Превышено время ожидания при попытке отправить звёзды")
            raise FragmentAPIError("Превышено время ожидания при попытке отправить звёзды") from exc
        except httpx.HTTPError as exc:
            logger.exception(f"Ошибка HTTP во время отправки звёзд: {exc}")
            raise FragmentAPIError(f"Ошибка HTTP во время отправки звёзд: {exc}") from exc

        if response.status_code == 200:
            return response.json()

        # response.status_code никогда не будет 401 судя по документации; если будет какая-то ошибка, то
        # response.status_code будет 400, и там будет указана ошибка со своей нумерацией из документации
        if response.status_code == 401 and retry_on_401:
            logger.debug("Токен fragment-api истек, обновляем и пробуем снова...")
            self.token = None
            await self._ensure_authenticated()
            return await self._send_stars_request(payload, retry_on_401=False)

        # TODO: в случае ошибки со стороны FragmentAPI, текст ошибки должен сохраняться в metadata транзакции
        #       для отслеживания истории, чтобы в случае чего тех. поддержка могла просмотреть подробности
        #       неудачной транзакции
        logger.error(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")
        raise FragmentAPIError(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")

    async def _get_headers(self, method: str) -> dict[str, str]:
        await self._ensure_authenticated()

        if method == "GET":
            return {
                "Accept": "application/json",
                "Authorization": f"JWT {self.token}",
            }
        elif method == "POST":
            return {
                "Accept": "application/json",
                "Authorization": f"JWT {self.token}",
                "Content-Type": "application/json",
            }
        else:
            raise ValueError(f"Invalid method for headers: {method}")

    async def _ensure_authenticated(self) -> None:
        if self.token:
            return

        await self._authenticate_fragment()

        if not self.token:
            logger.exception("Аутентификация во fragment-api провалена")
            raise FragmentAPIError("Аутентификация во fragment-api провалена")

    async def _authenticate_fragment(self) -> None:
        if not self.mnemonics:
            logger.error("Аутентификация невозможна: отсутствуют мнемоники.")
            raise FragmentAPIError("Отсутствуют мнемоники для аутентификации во fragment-api")

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
            logger.exception("Превышено время ожидания аутентификации во fragment-api")
            raise FragmentAPIError("Превышено время ожидания аутентификации во fragment-api") from exc
        except httpx.HTTPError as exc:
            logger.exception(f"Ошибка HTTP аутентификации во fragment-api: {exc}")
            raise FragmentAPIError(f"Ошибка HTTP аутентификации во fragment-api: {exc}") from exc

        if response.status_code != 200:
            logger.error(f"Ошибка авторизации fragment-api: {response.status_code = } - {response.text = }")
            raise FragmentAPIError(
                f"Аутентификация провалена: {response.status_code = } - {response.text = }"
            )

        token = response.json().get("token")
        if not token:
            raise FragmentAPIError("Аутентификация во fragment-api прошла успешно, но не хватает токена")

        self.token = token
        logger.debug("Успешная авторизация во fragment-api.")
