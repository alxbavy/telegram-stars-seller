from typing import final

from django.apps import AppConfig
from django.db.models import Transform, JSONField


@final
class CoreConfig(AppConfig):
    name = 'core'


@final
class SQLiteJsonNormalizer(Transform):
    lookup_name = "normalize"

    # Когда передаётся только сам JSON, SQLite ре-форматирует его, то есть отсортирует ключи в алфавитном порядке
    # (подойдёт не только эта SQLite функция, но неважно, какая)
    function = "json_remove"


_ = JSONField.register_lookup(SQLiteJsonNormalizer)
