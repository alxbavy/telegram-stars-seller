import time
import logging
from enum import StrEnum
from httpx import ConnectError, ConnectTimeout, PoolTimeout

from bot.utils.string_helpers import get_ending_for_digit_string, WordCase


SAFE_TO_RETRY = (ConnectError, ConnectTimeout, PoolTimeout)


logger = logging.getLogger(__name__)


class RetriesEntity(StrEnum):
    DB_TIME = "DB_TIME"
    NETWORK_TIME = "NETWORK_TIME"


class RetriesError(Exception):
    """Базовая ошибка перезапусков."""


class RetriesTimeoutError(RetriesError):
    def __init__(self, retries_entity: RetriesEntity, timeout: float, for_whom: str):
        timeout = abs(timeout)

        time_amount = timeout / 60.0
        time_unit = "минут"

        if time_amount < 1.0:
            time_amount = timeout
            time_unit = "секунд"

        ending = get_ending_for_digit_string(str(int(time_amount)), WordCase.NOMINATIVE)
        exceeded_time = f"({time_amount:.1f} {time_unit}{ending})"

        err_msg = f"Превышено время повторных попыток {exceeded_time} для "
        if retries_entity == RetriesEntity.DB_TIME:
            err_msg += f"обращения к БД ({for_whom})"
        elif retries_entity == RetriesEntity.NETWORK_TIME:
            err_msg += f"{for_whom}"

        super().__init__(err_msg)


class MaxRetriesError(RetriesError):
    def __init__(self, max_retries: int, for_whom: str):
        super().__init__(f"Превышено количество попыток ({max_retries}) для {for_whom}")


def get_timeout_error_or_none(
        retries_entity: RetriesEntity,
        started_at: float, timeout: float,
        for_whom: str
) -> RetriesTimeoutError | None:
    if time.time() - started_at > timeout:
        err = RetriesTimeoutError(retries_entity, timeout, for_whom)
        logger.exception(str(err))
        return err

    return None
