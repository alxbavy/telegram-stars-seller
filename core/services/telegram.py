from typing import NamedTuple
import os
import asyncio

from telethon import TelegramClient, errors
from telethon.types import User  # noqa


class IsUserExistsResult(NamedTuple):
    """
    `is_found = True` указывается только в том случае, если пользователь успешно найден, иначе всегда False.

    `username = {some str}` указывается только в том случае, если пользователь успешно найден, иначе всегда None.

    `msg = {some msg}` указывается в случаях, когда пользователь не найден; если пользователь не найден и
    `msg = None`, значит ошибка неизвестная.

    `is_retry, sleep_time_before_retry` указывается только в случае, когда телеграм запрашивает подождать дольше, чем
    мы готовы ждать по умолчанию (`client.flood_sleep_threshold`).
    """

    is_found: bool
    username: str | None = None
    msg: str | None = None
    is_retry: bool | None = None
    sleep_time_before_retry: float | None = None


class TelegramService:
    def __init__(self):
        return

        api_id_str: str | None = os.getenv("TELETHON_API_ID")
        if api_id_str is None:
            raise EnvironmentError("В .env файле не найден TELETHON_API_ID")
        if not api_id_str.isdigit():
            raise EnvironmentError("В .env файле TELETHON_API_ID должен быть указан в виде целого числа")
        api_id = int(api_id_str)

        api_hash: str | None = os.getenv("TELETHON_API_HASH")
        if api_hash is None:
            raise EnvironmentError("В .env файле не найден TELETHON_API_HASH")

        self.client: TelegramClient = TelegramClient('session', api_id, api_hash)

        # Настройка порога авто-ожидания (по умолчанию 10с)
        # Если Telegram скажет ждать больше 10с, код выбросит ошибку, а не уснет сам,
        # и она будет отловлена в self.resolve_username(...)
        self.client.flood_sleep_threshold = 10


    async def resolve_username(self, username: str, sleep_time: float | None = None) -> IsUserExistsResult:
        """
        Проверяет, существует ли пользователь в Telegram.

        По умолчанию есть задержка в `5` секунд перед исполнением кода.

        `sleep_time` отвечает за дополнительную задержку.
        """

        await asyncio.sleep(5)
        return IsUserExistsResult(True, username)

        if sleep_time:
            await asyncio.sleep(sleep_time)

        no_user_return_msg = "Введённый username не существует или невалиден"

        try:
            async with self.client:
                user = await self.client.get_entity(username)

            if not isinstance(user, User):
                return IsUserExistsResult(False, msg=no_user_return_msg)

            return IsUserExistsResult(True, user.username)

        except errors.FloodWaitError as e:
            # e.seconds - это время, которое требует подождать Telegram
            return IsUserExistsResult(
                False,
                msg=f"Слишком много запросов! Нужно подождать {e.seconds} секунд",
                is_retry=True,
                sleep_time_before_retry=float(e.seconds)
            )

        except errors.UsernameInvalidError:
            return IsUserExistsResult(
                False,
                msg=no_user_return_msg,
            )

        except Exception as e:
            return IsUserExistsResult(
                False,
                msg=str(e),
            )
