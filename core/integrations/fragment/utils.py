import re
from math import ceil
from typing import cast

from core.integrations.fragment.schemas import StarsJSON


def parse_retry_after(retry_after_str: str) -> int | None:
    """Возвращает кол-во секунд либо None."""
    digit_pattern = re.compile(r"(\d+)(s\b|ms\b|m\b)?")
    retry_after = digit_pattern.search(retry_after_str)

    if retry_after is None:
        return None

    retry_after_int = int(retry_after.group(1))
    measurement = cast(str, retry_after.group(2).strip())

    if not measurement or measurement == "s":
        return retry_after_int

    if measurement == "ms":
        retry_after_int = ceil(retry_after_int / 1000)
    elif measurement == "m":
        retry_after_int = retry_after_int * 60
    return retry_after_int


def get_prices_for_currency(stars_json: tuple[StarsJSON] | None, currency: str) -> StarsJSON | None:
    if stars_json is None:
        return None

    for price in stars_json:
        if price["currency"].lower() == currency:
            return price

    return None
