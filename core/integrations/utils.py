import asyncio
from httpx import Timeout
from collections.abc import Awaitable

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from core.integrations.fragment.errors import (
    FragmentAPINetworkError,
    FragmentAPITemporaryError,
    FragmentAPITooManyRequests
)
from core.integrations.platega.errors import PlategaAPINetworkError


def create_new_timeout_conf_or_use_default(timeout: float | None, connect: float | None, default: Timeout) -> Timeout:
    if timeout is not None and connect is not None:
        return Timeout(timeout=timeout, connect=connect)

    if timeout is not None:
        return Timeout(timeout=timeout)

    if connect is not None:
        return Timeout(timeout=default.read, connect=connect)

    return default


async def retries_with_tenacity[R](
        coro: Awaitable[R],
        *,
        attempts: int = 3,
        initial_wait: float = 1.0,
        max_wait: float = 10.0,
        jitter: float = 3.0
) -> R:
    async for attempt in AsyncRetrying(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
            retry=retry_if_exception_type((
                    FragmentAPINetworkError,
                    FragmentAPITemporaryError,
                    FragmentAPITooManyRequests,
                    PlategaAPINetworkError
            )),
            reraise=True
    ):
        with attempt:
            try:
                return await coro

            except FragmentAPITooManyRequests as err:
                time_to_sleep = float(err.retry_after) if err.retry_after is not None else 10.0
                time_to_sleep = time_to_sleep - attempt.retry_state.upcoming_sleep + 1
                if time_to_sleep > 0:
                    await asyncio.sleep(time_to_sleep)
                raise err

    return await coro
