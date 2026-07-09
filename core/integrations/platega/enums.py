from enum import StrEnum

from core.domain.enums import TransactionStatus


class PlategaStatus(StrEnum):
    PENDING = "PENDING"
    CANCELED = "CANCELED"
    CONFIRMED = "CONFIRMED"
    CHARGEBACKED = "CHARGEBACKED"

    @staticmethod
    def transform_into_internal_status_or_keep_original(platega_status: str) -> TransactionStatus | str:
        if platega_status == PlategaStatus.CONFIRMED:
            return TransactionStatus.PROCESSING

        elif platega_status == PlategaStatus.CANCELED:
            return TransactionStatus.CANCELLED

        elif platega_status == PlategaStatus.CHARGEBACKED:
            return TransactionStatus.CHARGEBACKED

        elif platega_status == PlategaStatus.PENDING:
            return TransactionStatus.PENDING

        return platega_status
