from typing import final
from enum import StrEnum


class TranslatedEnum(StrEnum):
    translation: str

    def __init__(self, enum_value: str) -> None:
        self.translation = enum_value

    @classmethod
    def to_choices(cls):
        return tuple((name.value, name.translation) for name in cls)


@final
class Translation:
    def __init__(self, translation: str) -> None:
        self.enum_name = ""
        self.translation = translation

    def __set_name__(self, owner: type[StrEnum], name: str) -> None:
        enum_name = name[1:]
        if enum_name not in owner:
            raise SyntaxError(f"{enum_name} must copy existing name with _ at the beginning")

        if name[:1] != "_":
            raise SyntaxError(f"Translation attr of {enum_name} must start with _")

        self.enum_name = enum_name
        enum_attr = getattr(owner, self.enum_name)
        enum_attr.translation = self.translation

    def __get__(self, instance: None, owner: type[StrEnum]) -> str:
        return self.translation


class TransactionStatus(TranslatedEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

    _PENDING = Translation("ОЖИДАЕТ")
    _SUCCESS = Translation("УСПЕШНО")
    _CANCELLED = Translation("ОТМЕНЕНО")
    _FAILED = Translation("ОШИБКА")


class TransactionType(TranslatedEnum):
    PURCHASE = "PURCHASE"

    _PURCHASE = Translation("Покупка")
