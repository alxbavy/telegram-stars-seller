class PlategaAPIError(Exception):
    """Базовая ошибка при работе с API Platega."""


class PlategaAPINetworkError(PlategaAPIError):
    """Ошибка сети, когда запрос точно НЕ был отправлен."""
