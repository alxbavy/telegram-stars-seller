"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from typing import Any, Callable
from collections.abc import Coroutine

from django.conf import settings
from django.core.asgi import get_asgi_application

from blacknoise import BlackNoise


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_application = get_asgi_application()


static_app = BlackNoise(django_asgi_application)
static_app.add(settings.BASE_DIR / "static", "/static")


AsgiMessage = dict[str, Any]
AsgiReceive = Callable[[], Coroutine[Any, Any, AsgiMessage]]
AsgiSend = Callable[[AsgiMessage], Coroutine[Any, Any, None]]

async def application(scope: dict[str, Any], receive: AsgiReceive, send: AsgiSend) -> None:
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        await static_app(scope, receive, send)
