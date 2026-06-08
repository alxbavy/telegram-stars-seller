import asyncio
import logging
from decimal import Decimal
from urllib.parse import urljoin
from typing import final, cast
from collections.abc import Mapping

import httpx

from django.conf import settings

from core.integrations.fragment.errors import FragmentAPIError, FragmentAPITooManyRequests, FragmentAPITemporaryError
from core.integrations.fragment.schemas import BalanceResponse, CurrentPricesResponse, HasCurrency, SendStarsResponse
from core.integrations.fragment.utils import parse_retry_after
from core.models import FragmentAPI


logger = logging.getLogger(__name__)


@final
class FragmentClient:
    GET_CURRENT_PRICES = "misc/prices/"
    GET_WALLET_BALANCE = "misc/wallet/"
    GET_USER_PATH = "misc/user/"
    SEND_STARS_PATH = "order/stars/"

    def __init__(self):
        self.url = cast(str, getattr(settings, "FRAGMENT_API_URL", None))
        self.currency = cast(str, getattr(settings, "FRAGMENT_CURRENCY", None))

        if not all([self.url, self.currency]):
            logger.error("fragment-api не сконфигурирован")
            raise ValueError("fragment-api не сконфигурирован")

        self.currency = self.currency.lower()
        if self.currency not in ["ton", "usdt_ton"]:
            logger.error("fragment-api принимает только ton или usdt_ton")
            raise ValueError("fragment-api принимает только ton или usdt_ton")

        self._client = httpx.AsyncClient(timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def resolve_username(self, username: str, delay: float | None = 3.0) -> bool:
        """
        Принимает `username`. Наличие знака `@` неважно. `username` должен начинаться с любой буквы, далее разрешены
        любые буквы, цифры и знак `_`. Длина `username` (без учёта `@`) - от `2` до `31` знаков.

        Можно указать время задержки `delay`. Если оно `None`, await не будет. Если `0.0`, await будет.

        Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::

            Некорректный `username`
            Таймауты
            HTTPError
            Ошибки аутентификации
            Неизвестные ошибки от fragment-api

        Returns:
            если пользователь найден - `True`, иначе `False`
        """

        if delay is not None:
            await asyncio.sleep(delay)

        username = username.lstrip("@")
        # Заглушка для тестов
        # if username == "True":
        #     return True
        # else:
        #     return False
        return await self._find_user_by_username(username)

    async def check_is_enough_currency_for_stars(self, amount_stars: int) -> None:
        bot_message = (
            "Не получилось проверить цены на бирже звёзд, чтобы убедиться, что бот сможет сделать автоматический "
            "перевод звёзд. Попробуй сделать покупку позже или обратись в тех. поддержку"
        )

        def _get_item[T: HasCurrency](iterable: tuple[T, ...]) -> T | None:
            for item in iterable:
                if item["currency"].lower() == self.currency:
                    return item
            return None

        current_prices = await self.get_current_prices()
        if current_prices is None:
            technical_message = "fragment-api вернул пустой список цен"
            logger.error(technical_message)
            raise FragmentAPITemporaryError(technical_message, bot_message)

        current_price = _get_item(current_prices)
        if current_price is None:
            technical_message = f'Не удалось найти цену звёзд для валюты "{self.currency}"'
            logger.error(technical_message)
            raise FragmentAPITemporaryError(technical_message, bot_message)

        balances = await self.get_wallet_balances()
        balance = _get_item(balances)
        if balance is None:
            technical_message = f'Не удалось найти баланс для валюты "{self.currency}"'
            logger.error(technical_message)
            raise FragmentAPITemporaryError(technical_message, bot_message)

        amount_stars_to_quantity_ratio = Decimal(amount_stars / current_price["quantity"])
        total_price =  amount_stars_to_quantity_ratio * Decimal(current_price["price"])

        balance_amount = Decimal(balance["amount"])
        if balance_amount - total_price < 0:
            technical_message = f'На балансе не хватает средств в валюте "{self.currency}", {total_price = }, {balance_amount = }'
            logger.error(technical_message)
            bot_message = (
                f"В данный момент у бота нет возможности перевести {amount_stars} звёзд"
                f'{". Попробуй выбрать меньшее количество" if amount_stars > 50 else " — обратись в тех. поддержку"}'
            )
            raise FragmentAPITemporaryError(technical_message, bot_message)

        return None

    async def send_stars(self, username: str, amount_stars: int) -> SendStarsResponse:
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

        Также, может выбросить одно из следующих исключений::

            FragmentAPITemporaryError

        Для отображения информации об ошибках пользователю их следует отлавливать либо в `error_handler`, либо,
        если такой возможности нет, с помощью `try except`.
        """
        # Заглушка для тестов
        # return {
        #     "success": True,
        #     "receiver": "dummy_receiver",
        #     "sender": {"phone_number": "dummy_phone_number"},
        #     "price": {"currency": self.currency, "amount": "1337.0"},
        #     "fee": {"currency": self.currency, "amount": "1337.0"},
        #     "ref_id": "dummy_ref_id",
        #     "status": "dummy_status",
        #     "type": "dummy_type",
        #     "error": "dummy_error",
        #     "created_at": "dummy_created_at",
        # }

        username = username.lstrip("@").strip()

        if not username:
            error_msg = "username нельзя быть пустым при переводе звёзд"
            logger.exception(error_msg)
            raise FragmentAPIError(error_msg)

        if not isinstance(amount_stars, int):
            error_msg = f"В качестве количества звёзд был передан неправильный объект = {amount_stars}"
            logger.exception(error_msg)
            raise FragmentAPIError(error_msg)

        if amount_stars < 50:
            error_msg = "Количество звёзд должно быть больше 50"
            logger.exception(error_msg)
            raise FragmentAPIError(error_msg)

        if not await self.resolve_username(username, delay=None):
            error_msg = f"Не найден {username}"
            logger.error(error_msg)
            raise FragmentAPIError(error_msg)

        await self.check_is_enough_currency_for_stars(amount_stars)

        payload = {
            "username": username,
            "quantity": amount_stars,
            "show_sender": False,
            "currency": self.currency
        }

        return await self._send_stars_request(payload)

    async def get_current_prices(self):
        response = await self._make_request("GET", self.GET_CURRENT_PRICES)
        response_data = cast(CurrentPricesResponse, response.json())
        return response_data["stars"]

    async def get_wallet_balances(self):
        response = await self._make_request("GET", self.GET_WALLET_BALANCE)
        response_data = cast(BalanceResponse, response.json())
        return response_data["balances"]

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
        response = await self._make_request("GET", f"{self.GET_USER_PATH}{username}/")

        if response.status_code == 200:
            return True

        if response.status_code == 404:
            return False

        if response.status_code == 400:
            logger.error(f"Произошла неизвестная ошибка со стороны fragment-api:\n{response.json() = }")
            raise FragmentAPIError(f"Произошла неизвестная ошибка со стороны fragment-api:\n{response.json() = }")

        logger.exception(f"Неизвестный ответ от сервера fragment-api: {response.status_code = }")
        raise FragmentAPIError(
            f"Неизвестный ответ от сервера fragment-api:\n{response.status_code = } - {response.text = }"
        )

    async def _send_stars_request(self, payload: dict[str, str | int | bool]) -> SendStarsResponse:
        response = await self._make_request("POST", self.SEND_STARS_PATH, payload)

        if response.status_code == 200:
            response_data = cast(SendStarsResponse, response.json())
            return response_data

        logger.error(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")
        raise FragmentAPIError(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")

    async def _make_request(
            self,
            method: str, path: str, data: Mapping[str, object] | None = None,
            timeout: float = 30.0, retry_on_429: bool = True
    ) -> httpx.Response:
        headers = await self._get_headers(method)
        full_url = urljoin(self.url, path)

        try:
            if method == "POST":
                response = await self._client.post(full_url, json=data, headers=headers, timeout=timeout)
            else:
                response = await self._client.get(full_url, headers=headers, timeout=timeout)

        except httpx.TimeoutException as exc:
            logger.exception(f"Превышено время ожидания при обращении к fragment-api")
            raise FragmentAPIError("Превышено время ожидания при обращении к fragment-api") from exc

        except httpx.HTTPError as exc:
            logger.exception(f"Ошибка HTTP во время обращения к fragment-api: {exc}")
            raise FragmentAPIError(f"Ошибка HTTP во время обращения к fragment-api: {exc}") from exc

        if response.status_code in [401, 403]:
            logger.debug(f"Токен fragment-api истек;\n{response.status_code = } - {response.text = }")
            raise FragmentAPIError("Токен fragment-api истек")

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "missing")
            error_msg = f"Слишком много запросов по пути {full_url}"

            if retry_after == "missing":
                retry_after = None

            if isinstance(retry_after, str):
                retry_after = parse_retry_after(retry_after)
            elif not isinstance(retry_after, (int, float)):
                retry_after = None

            if retry_after is not None:
                if retry_on_429 and retry_after <= 30.0:
                    await asyncio.sleep(retry_after)
                    return await self._make_request(method, path, data=data, timeout=timeout, retry_on_429=False)
                else:
                    error_msg += f", {retry_after = }s"

            logger.exception(error_msg)
            raise FragmentAPITooManyRequests(retry_after, error_msg)

        return response

    async def _get_headers(self, method: str) -> dict[str, str]:
        token = (await FragmentAPI.aget_solo()).token
        if not token:
            logger.exception("Токен fragment-api отсутствует")
            raise FragmentAPIError("Токен fragment-api отсутствует")

        if method == "GET":
            return {
                "Accept": "application/json",
                "Authorization": f"JWT {token}",
            }
        elif method == "POST":
            return {
                "Accept": "application/json",
                "Authorization": f"JWT {token}",
                "Content-Type": "application/json",
            }
        else:
            raise ValueError(f"Invalid method for headers: {method}")


# Версия клиента с методами, которые можно использовать для автоматического создания токена по нажатию на кнопку в админ-панели.
# Код незаконченный, но вроде для получения токена всё есть. В любом случае в таком виде этот класс для создания токена
# по нажатию кнопки в админ-панели не пригоден
# @final
# class FragmentClientV2:
#     AUTH_PATH = "auth/authenticate/"
#     SEND_STARS_PATH = "order/stars/"
#     GET_USER_PATH = "misc/user/"
#
#     def __init__(self):
#         self.url = cast(str, getattr(settings, "FRAGMENT_API_URL", None))
#         self.api_key = cast(str, getattr(settings, "FRAGMENT_API_KEY", None))
#         self.mnemonics = cast(str, getattr(settings, "FRAGMENT_MNEMONICS", None))
#         self.phone = cast(str, getattr(settings, "FRAGMENT_PHONE", None))
#         self.wallet_version = cast(str, getattr(settings, "TON_WALLET_VERSION", None))
#
#         if not all([self.url, self.api_key, self.mnemonics, self.phone, self.wallet_version]):
#             logger.error("FragmentAPI не сконфигурирован.")
#             raise ValueError("FragmentAPI is not configured properly")
#
#         mnemonics_len = len(self.mnemonics.strip().split())
#         if mnemonics_len != 24:
#             logger.error(f"Не хватает слов в FragmentAPI mnemonics, сейчас их {mnemonics_len}")
#             raise ValueError(f"There's not enough words in FragmentAPI mnemonics, now length is {mnemonics_len} words")
#
#         if not self.phone[0].isdigit():
#             self.phone = self.phone [1:]
#
#         phone_len = len(self.phone)
#         if phone_len != 11:
#             logger.error(f"Номер телефона должен содержать 11 цифр (в начале может быть опционально знак +), сейчас их {phone_len}")
#             raise ValueError(f"Phone number must contain 11 digits (may be optional + in the beginning), now length is {phone_len} digits")
#
#         self._client = httpx.AsyncClient(timeout=30.0)
#
#         self.is_authentication_failed = False
#         with ThreadPoolExecutor() as executor:
#             future_fragment_api = executor.submit(asyncio.run, FragmentAPI.aget_solo())
#             self.token = future_fragment_api.result(15.0).token
#
#             if not self.token:
#                 future_authentication = executor.submit(asyncio.run, self._authenticate_fragment(60.0))
#                 future_authentication.result(70.0)
#
#     async def aclose(self) -> None:
#         await self._client.aclose()
#
#     async def resolve_username(self, username: str, delay: float | None = 5.0) -> bool:
#         """
#         Принимает `username`. Наличие знака `@` неважно. `username` должен начинаться с любой буквы, далее разрешены
#         любые буквы, цифры и знак `_`. Длина `username` (без учёта `@`) - от `2` до `31` знаков.
#
#         Можно указать время задержки `delay`. Если оно `None`, await не будет. Если `0.0`, await будет.
#
#         Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::
#
#             Некорректный `username`
#             Таймауты
#             HTTPError
#             Ошибки аутентификации
#             Неизвестные ошибки от fragment-api
#
#         Returns:
#             если пользователь найден - `True`, иначе `False`
#         """
#         if delay is not None:
#             await asyncio.sleep(delay)
#
#         username = username.lstrip("@")
#         # if username == "True":
#         #     return True
#         # else:
#         #     return False
#         return await self._find_user_by_username(username)
#
#     async def send_stars(self, username: str, amount_stars: int) -> FragmentResponse:
#         """
#         Принимает `username` и `amount_stars`.
#
#         `amount_stars` в текущем виде проверяются во фронте.
#
#         `username` проверяется во fragment-api, поэтому в случае некорректного username будет ошибка 400.
#
#         Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::
#
#             Некорректный `username`
#             Таймауты
#             HTTPError
#             Ошибки аутентификации
#             Неизвестные ошибки от fragment-api
#
#         Ошибки `FragmentAPIError` следует отлавливать для отображения информации об ошибках пользователю.
#         """
#         # return {
#         #     "success": True,
#         #     "receiver": "dummy_receiver",
#         #     "sender": {"phone_number": "dummy_phone_number"},
#         #     "ton_price": "dummy_ton_pice",
#         #     "fee_ton": "dummy_fee_ton",
#         #     "ref_id": "dummy_ref_id",
#         #     "status": "dummy_status",
#         #     "type": "dummy_type",
#         #     "error": "dummy_error",
#         #     "created_at": "dummy_created_at",
#         # }
#
#         username = username.strip()
#
#         if not username:
#             logger.exception("username нельзя быть пустым при переводе звёзд")
#             raise FragmentAPIError("username нельзя быть пустым при переводе звёзд")
#
#         if not isinstance(amount_stars, int):
#             logger.exception(f"в качестве количества звёзд был передан неправильный объект = {amount_stars}")
#             raise FragmentAPIError(f"в качестве количества звёзд был передан неправильный объект = {amount_stars}")
#         if amount_stars < 50:
#             logger.exception("количество звёзд должно быть больше 50")
#             raise FragmentAPIError("количество звёзд должно быть больше 50")
#
#         if not await self.resolve_username(username, delay=None):
#             logger.error(f"Не найден {username} ")
#             raise FragmentAPIError(f"Не найден {username}")
#
#         payload = {
#             "username": username,
#             "quantity": amount_stars,
#             "show_sender": False
#         }
#
#         return await self._send_stars_request(payload)
#
#     async def _find_user_by_username(self, username: str) -> bool:
#         """
#         Принимает username без знака `@`.
#
#         Может выбросить `FragmentAPIError` (по смыслу, текст ошибок может отличаться)::
#
#             Некорректный `username`
#             Таймауты
#             HTTPError
#             Ошибки аутентификации
#             Неизвестные ошибки от fragment-api
#
#         Returns:
#             если пользователь найден - `True`, иначе `False`
#         """
#         # await self._ensure_authenticated()
#
#         # headers = await self._get_headers("GET")
#
#         response = await self._make_request("GET", f"{self.GET_USER_PATH}{username}/")
#
#         # try:
#         #     response = await self._client.get(
#         #         urljoin(self.url, f"{self.GET_USER_PATH}{username}/"),
#         #         headers=headers,
#         #         timeout=30.0
#         #     )
#         # except httpx.TimeoutException as exc:
#         #     logger.exception("Превышено время ожидания от fragment-api при проверке username")
#         #     raise FragmentAPIError("Превышено время ожидания от fragment-api при проверке username") from exc
#         # except httpx.HTTPError as exc:
#         #     logger.exception("Ошибка HTTP от fragment-api при проверке username")
#         #     raise FragmentAPIError(f"Ошибка HTTP от fragment-api при проверке username: {e}") from exc
#
#         if response.status_code == 200:
#             return True
#
#         if response.status_code == 404:
#             return False
#
#         if response.status_code == 400:
#             logger.error(f"Произошла неизвестная ошибка со стороны fragment-api:\n{response.json() = }")
#             raise FragmentAPIError(f"Произошла неизвестная ошибка со стороны fragment-api:\n{response.json() = }")
#
#         logger.exception(f"Неизвестный ответ от сервера fragment-api: {response.status_code = }")
#         raise FragmentAPIError(
#             f"Неизвестный ответ от сервера fragment-api:\n{response.status_code = } - {response.text = }"
#         )
#
#     async def _send_stars_request(
#             self,
#             payload: dict[str, str | int | bool],
#             retry_on_401: bool=True
#     ) -> FragmentResponse:
#         # await self._ensure_authenticated()
#
#         # headers = await self._get_headers("POST")
#
#         response = await self._make_request("POST", self.SEND_STARS_PATH, payload)
#         # try:
#         #     response = await self._client.post(
#         #         urljoin(self.url, self.SEND_STARS_PATH),
#         #         json=payload,
#         #         headers=headers,
#         #         timeout=30.0
#         #     )
#         # except httpx.TimeoutException as exc:
#         #     logger.exception(f"Превышено время ожидания при попытке отправить звёзды")
#         #     raise FragmentAPIError("Превышено время ожидания при попытке отправить звёзды") from exc
#         # except httpx.HTTPError as exc:
#         #     logger.exception(f"Ошибка HTTP во время отправки звёзд: {exc}")
#         #     raise FragmentAPIError(f"Ошибка HTTP во время отправки звёзд: {exc}") from exc
#
#         if response.status_code == 200:
#             response_data = cast(FragmentResponse, response.json())
#             return response_data
#
#         # response.status_code никогда не будет 401 судя по документации; если будет какая-то ошибка, то
#         # response.status_code будет 400, и там будет указана ошибка со своей нумерацией из документации
#         # if response.status_code == 401 and retry_on_401:
#         #     logger.debug("Токен fragment-api истек, обновляем и пробуем снова...")
#         #     self.token = None
#         #     await self._ensure_authenticated()
#         #     return await self._send_stars_request(payload, retry_on_401=False)
#
#         logger.error(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")
#         raise FragmentAPIError(f"Не удалось отправить звёзды: {response.status_code = } - {response.text = }")
#
#     def _get_headers(self, method: str) -> dict[str, str]:
#         if not self.token:
#             logger.exception("Токен fragment-api отсутствует")
#             raise FragmentAPIError("Токен fragment-api отсутствует")
#
#         if method == "GET":
#             return {
#                 "Accept": "application/json",
#                 "Authorization": f"JWT {self.token}",
#             }
#         elif method == "POST":
#             return {
#                 "Accept": "application/json",
#                 "Authorization": f"JWT {self.token}",
#                 "Content-Type": "application/json",
#             }
#         else:
#             raise ValueError(f"Invalid method for headers: {method}")
#
#     async def _make_request(
#             self,
#             method: str, path: str, data: Mapping[str, object] | None = None,
#             timeout: float = 30.0, retry: bool = True
#     ) -> httpx.Response:
#         headers = self._get_headers(method)
#         full_url = urljoin(self.url, path)
#
#         try:
#             if method == "POST":
#                 json_data = json.dumps(data).encode("utf-8")
#                 response = await self._client.post(full_url, json=json_data, headers=headers, timeout=timeout)
#             else:
#                 response = await self._client.get(full_url, headers=headers, timeout=timeout)
#
#         except httpx.TimeoutException as exc:
#             logger.exception(f"Превышено время ожидания при обращении к fragment-api")
#             raise FragmentAPIError("Превышено время ожидания при обращении к fragment-api") from exc
#
#         except httpx.HTTPError as exc:
#             logger.exception(f"Ошибка HTTP во время обращения к fragment-api: {exc}")
#             raise FragmentAPIError(f"Ошибка HTTP во время обращения к fragment-api: {exc}") from exc
#
#         if response.status_code in [401, 403]:
#             logger.debug(f"Токен fragment-api истек;\n{response.status_code = } - {response.text = }")
#             raise FragmentAPIError("Токен fragment-api истек")
#
#
#         return response
#
#     async def _ensure_authenticated(self) -> None:
#         if self.token:
#             return
#
#         await self._authenticate_fragment()
#
#         if not self.token:
#             logger.exception("Аутентификация во fragment-api провалена")
#             raise FragmentAPIError("Аутентификация во fragment-api провалена")
#
#     async def _authenticate_fragment(self, timeout: float = 15.0) -> None:
#         payload = {
#             "api_key": self.api_key,
#             "phone_number": self.phone,
#             "mnemonics": self.mnemonics.strip().split(),
#             "version": self.wallet_version
#         }
#
#         try:
#             response = await self._client.post(
#                 urljoin(self.url, self.AUTH_PATH),
#                 json=payload,
#                 timeout=timeout
#             )
#
#         except httpx.TimeoutException as exc:
#             logger.exception("Превышено время ожидания аутентификации во fragment-api")
#             raise FragmentAPIError("Превышено время ожидания аутентификации во fragment-api") from exc
#
#         except httpx.HTTPError as exc:
#             logger.exception(f"Ошибка HTTP аутентификации во fragment-api: {exc}")
#             raise FragmentAPIError(f"Ошибка HTTP аутентификации во fragment-api: {exc}") from exc
#
#         finally:
#             self.is_authentication_failed = True
#
#         if response.status_code != 200:
#             self.is_authentication_failed = True
#             logger.error(f"Ошибка авторизации fragment-api: {response.status_code = } - {response.text = }")
#             raise FragmentAPIError(
#                 f"Аутентификация провалена: {response.status_code = } - {response.text = }"
#             )
#
#         token = cast(str, response.json().get("token"))
#         if not token:
#             self.is_authentication_failed = True
#             logger.exception("Аутентификация во fragment-api прошла успешно, но не хватает токена")
#             raise FragmentAPIError("Аутентификация во fragment-api прошла успешно, но не хватает токена")
#
#         self.token = token
#
#         fragment_api = await FragmentAPI.aget_solo()
#         fragment_api.token = token
#         await fragment_api.asave(update_fields=["token", "updated_at"])
#
#         logger.debug("Успешная авторизация во fragment-api.")
