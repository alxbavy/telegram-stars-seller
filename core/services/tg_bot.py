from typing import cast

from telegram.ext import ExtBot
from telegram.request import HTTPXRequest

from django.conf import settings


# По умолчанию connection_pool_size=1. Если воркер Celery многопоточный (concurrency > 1),
# этот пул нужно УВЕЛИЧИТЬ, иначе таски будут ждать свободного коннекта.
tg_request = HTTPXRequest(
    connection_pool_size=2,
    connect_timeout=20.0,
    read_timeout=25.0,
    write_timeout=25.0,
    media_write_timeout=60.0
)

bot = ExtBot(
    token=cast(str, settings.TELEGRAM_BOT_TOKEN),
    request=tg_request
)
