from enum import StrEnum


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class TransactionType(StrEnum):
    PURCHASE = "PURCHASE"
