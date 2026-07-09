from uuid import UUID
from typing import final

from core.integrations.fragment.enums import FragmentStatus
from core.repositories.fragment_transaction import FragmentTransactionRepository
from core.models import FragmentTransaction


@final
class FragmentTransactionService:
    def __init__(self, fragment_tx_repo: FragmentTransactionRepository) -> None:
        self._fragment_tx_repo = fragment_tx_repo

    async def create_transaction(self, fragment_tx_id: UUID, payment_api_id: UUID, status: FragmentStatus) -> FragmentTransaction:
        transaction = await self._fragment_tx_repo.get_by_fragment_id(fragment_tx_id)
        if transaction is not None:
            return transaction

        return await self._fragment_tx_repo.create_transaction(fragment_tx_id, payment_api_id, status)

    async def get_by_fragment_id(self, fragment_tx_id: UUID) -> FragmentTransaction | None:
        return await self._fragment_tx_repo.get_by_fragment_id(fragment_tx_id)

    async def get_fragment_api_jwt_token(self) -> str:
        return await self._fragment_tx_repo.get_fragment_api_jwt_token()

    async def update_status_by_id(self, fragment_tx_id: UUID, status: FragmentStatus) -> bool:
        return await self._fragment_tx_repo.update_status_by_id(fragment_tx_id, status)
