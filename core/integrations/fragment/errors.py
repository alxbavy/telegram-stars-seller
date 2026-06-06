from decimal import Decimal
from typing import final


class FragmentAPIError(Exception):
    """Базовая ошибка клиента Fragment API."""


@final
class FragmentAPITooManyRequests(Exception):
    """Ошибка для HTTP со статусом 429."""
    def __init__(self, retry_after: int | float | None = None, message: str | None = None) -> None:
        self.retry_after = retry_after
        self.message = message
        super().__init__(self.message)


@final
class FragmentAPITemporaryError(Exception):
    def __init__(self, technical_message: str, bot_message: str) -> None:
        self.technical_message = technical_message
        self.bot_message = bot_message
        super().__init__(self.technical_message)


@final
class FragmentAPIWalletError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


@final
class FragmentAPIUsernameNotFoundError(Exception):
    def __init__(self, username: str, message: str | None = None) -> None:
        self.username = username
        self.message = message
        super().__init__(self.message)
