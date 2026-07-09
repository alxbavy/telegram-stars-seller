from typing import final, cast
from enum import StrEnum


class TranslatedEnum(StrEnum):
    translation: str

    def __init__(self, enum_value: str) -> None:
        self.translation = enum_value

    @classmethod
    def to_choices(cls):
        return tuple((name.value, name.translation) for name in cls)

    @classmethod
    def all_enums[T: StrEnum](cls: type[T]) -> tuple[T, ...]:
        return tuple(enum_element for enum_element in cls)


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
        enum_attr = cast(TranslatedEnum, getattr(owner, self.enum_name))
        enum_attr.translation = self.translation

    def __get__(self, instance: None, owner: type[StrEnum]) -> str:
        return self.translation


class TransactionStatus(TranslatedEnum):
    # При добавлении статусов необходимо обновлять FINAL_STATUSES и NOT_FINAL_STATUSES
    # Статус считается неизвестным, если он не относится к FINAL_STATUSES и NOT_FINAL_STATUSES
    # NOT_FINAL_STATUSES равносильны PROCESSING
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENDING = "SENDING"
    SEND_CREATED = "SEND_CREATED"
    IN_DOUBT = "IN_DOUBT"
    CHARGEBACKED = "CHARGEBACKED"
    SUCCESS = "SUCCESS"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

    _PENDING = Translation("ОЖИДАЕТ")
    _PROCESSING = Translation("В ПРОЦЕССЕ")
    _SENDING = Translation("В ОТПРАВКЕ")
    _SEND_CREATED = Translation("ОТПРАВЛЕНО")
    _IN_DOUBT = Translation("ПОД СОМНЕНИЕМ")
    _CHARGEBACKED = Translation("ВОЗВРАТ")
    _SUCCESS = Translation("УСПЕШНО")
    _CANCELLED = Translation("ОТМЕНЕНО")
    _FAILED = Translation("ОШИБКА")


class TransactionType(TranslatedEnum):
    PURCHASE = "PURCHASE"

    _PURCHASE = Translation("Покупка")


# Известные статусы для финального сообщения
FINAL_MSG_STATUSES = (
    TransactionStatus.SUCCESS,
    TransactionStatus.FAILED,
    TransactionStatus.IN_DOUBT,
    TransactionStatus.CANCELLED,
    TransactionStatus.CHARGEBACKED,
)


PROCESSING_STATUSES = (
    TransactionStatus.PROCESSING,
    TransactionStatus.SENDING,
    TransactionStatus.SEND_CREATED,
)


ALL_STATUSES = TransactionStatus.all_enums()


STATUS_TRANSITION_MATRIX: dict[TransactionStatus | str, tuple[TransactionStatus, ...]] = {
    TransactionStatus.PENDING: (
        TransactionStatus.PENDING,
        TransactionStatus.CANCELLED, TransactionStatus.PROCESSING, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.PROCESSING: (
        TransactionStatus.PROCESSING, TransactionStatus.SENDING, TransactionStatus.CANCELLED
    ),
    TransactionStatus.SENDING: (  # Тут переход сам в себя запрещён!
        TransactionStatus.SEND_CREATED,
        TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.IN_DOUBT, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.SEND_CREATED: (
        TransactionStatus.SEND_CREATED,
        TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.IN_DOUBT, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.SUCCESS: (
        TransactionStatus.SUCCESS, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.FAILED: (
        TransactionStatus.FAILED, TransactionStatus.SUCCESS, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.IN_DOUBT: (
        TransactionStatus.IN_DOUBT,
        TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.CANCELLED: (
        TransactionStatus.CANCELLED,TransactionStatus.IN_DOUBT,
        TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.CHARGEBACKED
    ),
    TransactionStatus.CHARGEBACKED: (TransactionStatus.CHARGEBACKED, ),
}


def get_translation(status: str) -> str:
    """
    Возвращает либо перевод из `TransactionStatus`, либо `исходную строку`, если перевод не найден.
    """
    translations = TransactionStatus.to_choices()

    for translation in translations:
        if status == translation[0]:
            return translation[1]

    return status


def is_change_status_allowed(current_status: str, new_status: str) -> bool:
    allowed_statuses = STATUS_TRANSITION_MATRIX.get(current_status)

    if allowed_statuses is None:
        return new_status in [
            TransactionStatus.PENDING, TransactionStatus.PROCESSING,
            TransactionStatus.CANCELLED, TransactionStatus.CHARGEBACKED
        ] or new_status not in ALL_STATUSES

    if new_status in allowed_statuses:
        return True

    return (
            new_status not in ALL_STATUSES
            and current_status in [TransactionStatus.PENDING, TransactionStatus.PROCESSING]
    )
