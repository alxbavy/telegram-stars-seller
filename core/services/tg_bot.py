import socket
from typing import cast

from telegram.ext import ExtBot
from telegram.request import HTTPXRequest

from django.conf import settings


linux_socket_options = [
    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
    (socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30),  # Проверка живого соединения каждые 30 сек (для очистки незакрытых соединений)
    (socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5),
    (socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3),
]


# По умолчанию connection_pool_size=1. Если воркер Celery многопоточный (concurrency > 1),
# этот пул нужно УВЕЛИЧИТЬ, иначе таски будут ждать свободного коннекта.
tg_request = HTTPXRequest(
    connection_pool_size=2,
    connect_timeout=10.0,
    read_timeout=15.0,
    write_timeout=15.0,
    media_write_timeout=60.0,
    socket_options=linux_socket_options
)

bot = ExtBot(
    token=cast(str, settings.TELEGRAM_BOT_TOKEN),
    request=tg_request
)
