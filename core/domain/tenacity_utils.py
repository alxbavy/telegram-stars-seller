import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import TypedDict

from telegram.error import RetryAfter, NetworkError

from tenacity import RetryCallState, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from general.utils import cast_force

from core.domain.type_aliases import AsyncCallable

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    attempts: int = 3
    initial_wait: float = 1.0
    max_wait: float = 10.0
    jitter: float = 3.0


async def sleep_for_retry_after(retry_state: RetryCallState) -> None:
    try:
        exc = retry_state.outcome.exception(5.0)

    except Exception as exc:
        logger.exception(f"{exc.__class__.__name__} - {str(exc)}")
        return

    if isinstance(exc, RetryAfter):
        retry_after = exc.retry_after

        time_to_sleep = float(retry_after) if isinstance(retry_after, int) else retry_after.total_seconds()
        time_to_sleep = time_to_sleep - retry_state.upcoming_sleep + 1
        if time_to_sleep > 0.0:
            await asyncio.sleep(time_to_sleep)


class TelegramRetryConfigDict(TypedDict):
    stop: stop_after_attempt
    wait: wait_exponential_jitter
    retry: retry_if_exception_type
    before_sleep: AsyncCallable[[RetryCallState], None]
    reraise: bool


@dataclass(frozen=True, slots=True)
class TelegramRetryConfig:
    stop: stop_after_attempt = stop_after_attempt(2)
    wait : wait_exponential_jitter = wait_exponential_jitter(initial=1.0, max=4.0, jitter=1.0)
    retry: retry_if_exception_type = retry_if_exception_type((NetworkError, RetryAfter))
    before_sleep: AsyncCallable[[RetryCallState], None] = sleep_for_retry_after
    reraise: bool = True

    @property
    def asdict(self) -> TelegramRetryConfigDict:
        return cast_force(TelegramRetryConfigDict, asdict(self))
