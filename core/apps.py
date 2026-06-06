from collections.abc import Mapping

from django.apps import AppConfig
from django.dispatch import receiver
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created


class CoreConfig(AppConfig):
    name = 'core'


@receiver(connection_created)
def configure_sqlite(sender: object, connection: BaseDatabaseWrapper, **kwargs: Mapping[str, object]):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")    # Для параллельного чтения
        cursor.execute("PRAGMA busy_timeout = 10000;")  # При одновременной записи будет ожидание, указывается в мс
        cursor.execute("PRAGMA synchronous = NORMAL;")  # Синхронизация с диском
