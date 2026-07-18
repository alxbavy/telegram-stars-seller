import asyncio
import logging
from dataclasses import dataclass

from telegram.error import RetryAfter
from tenacity import RetryCallState

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    attempts: int = 3
    initial_wait: float = 1.0
    max_wait: float = 10.0
    jitter: float = 3.0


async def sleep_for_retry_after(retry_state: RetryCallState):
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
