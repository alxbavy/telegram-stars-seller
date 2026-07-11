"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from collections.abc import Coroutine

from django.conf import settings
from django.core.asgi import get_asgi_application

from blacknoise import BlackNoise


_ = os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

logger = logging.getLogger(__name__)


django_asgi_application = get_asgi_application()


static_app = BlackNoise(django_asgi_application)
static_app.add(settings.BASE_DIR / "static", "/static")


AsgiMessage = dict[str, object]
AsgiReceive = Callable[[], Coroutine[object, object, AsgiMessage]]
AsgiSend = Callable[[AsgiMessage], Coroutine[object, object, None]]

async def application(scope: dict[str, object], receive: AsgiReceive, send: AsgiSend) -> None:
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()

            if message['type'] == 'lifespan.startup':
                loop = asyncio.get_running_loop()
                loop.set_default_executor(ThreadPoolExecutor(max_workers=50))
                logger.info("Server: ThreadPoolExecutor extended to 50 workers.")

                await send({'type': 'lifespan.startup.complete'})

            elif message['type'] == 'lifespan.shutdown':
                logger.info("Server is stopping, closing dishka container...")

                from core.ioc import close_container

                await close_container()

                logger.info("Dishka container closed successfully!")
                await send({'type': 'lifespan.shutdown.complete'})
                return

    else:
        await static_app(scope, receive, send)
