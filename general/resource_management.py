import logging
from typing import override

logger = logging.getLogger(__name__)


class Where:
    def __init__(self, where: str) -> None:
        self.where: str = f"{' ' + where if where else ''}"

    @override
    def __str__(self) -> str:
        return self.where


async def close_dishka_container(where: Where) -> None:
    logger.info(f"Closing DI container{where}...")
    from core.ioc import close_container
    await close_container()
    logger.info(f"DI container{where} closed successfully!")


async def close_async_redis_client(where: Where) -> None:
    logger.info(f"Closing async redis client{where}...")
    from core.services.redis_service import close_async_redis_client
    await close_async_redis_client()
    logger.info(f"Async redis client{where} closed successfully!")


async def close_resources(where: Where) -> None:
    try:
        await close_dishka_container(where)
    except Exception as err:
        logger.error(f"Error while closing DI container{where}: {err}")

    try:
        await close_async_redis_client(where)
    except Exception as err:
        logger.error(f"Error while closing async redis client{where}: {err}")
