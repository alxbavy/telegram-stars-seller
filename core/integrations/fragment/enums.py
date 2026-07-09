from core.domain.enums import TranslatedEnum, Translation, TransactionStatus


class FragmentStatus(TranslatedEnum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKCHAIN_SENT = "BLOCKCHAIN_SENT"

    _CREATED = Translation("CREATED")
    _PENDING = Translation("PENDING")
    _COMPLETED = Translation("COMPLETED")
    _FAILED = Translation("FAILED")
    _BLOCKCHAIN_SENT = Translation("BLOCKCHAIN_SENT")

    @staticmethod
    def transform_into_internal_status_or_keep_original(fragment_status: str) -> TransactionStatus | str:
        if fragment_status == FragmentStatus.CREATED or fragment_status == FragmentStatus.PENDING:
            return TransactionStatus.SEND_CREATED

        elif fragment_status == FragmentStatus.COMPLETED:
            return TransactionStatus.SUCCESS

        elif fragment_status == FragmentStatus.FAILED:
            return TransactionStatus.FAILED

        return TransactionStatus.IN_DOUBT  # В том числе BLOCKCHAIN_SENT
