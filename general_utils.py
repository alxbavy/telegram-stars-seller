import json
import logging
from decimal import Decimal
from dataclasses import is_dataclass, asdict
from typing import cast, override


logger = logging.getLogger(__name__)


def cast_force[C](_: type[C], source: object, /) -> C:
    return cast(C, source)  # noqa


class DataclassEncoder(json.JSONEncoder):
    @override
    def default(self, o: object):
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)  # noqa
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)  # pyright: ignore[reportAny]


def json_dumps(
        obj: object,
        *,
        ensure_ascii: bool = False, indent: int | None = None,
        skip_keys: bool = False,
        sort_keys: bool = False
) -> str:
    return json.dumps(
        obj, cls=DataclassEncoder,
        ensure_ascii=ensure_ascii, indent=indent,
        skipkeys=skip_keys,
        sort_keys=sort_keys
    )


def json_loads(string: str | bytes | bytearray) -> object:
    return cast(object, json.loads(string))


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
