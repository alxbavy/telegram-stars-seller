from uuid import UUID

from django.db.models import Case, When, F
from django.db.models.functions import Now

from core.integrations.fragment.enums import FragmentStatus
from core.integrations.fragment.schemas import FragmentTransactionKwargs
from core.models import FragmentTransaction, FragmentAPI


class FragmentTransactionRepository:
    model: type[FragmentTransaction] = FragmentTransaction
    model_api: type[FragmentAPI] = FragmentAPI

    async def create_transaction(
            self,
            fragment_tx_id: UUID,
            transaction_id: UUID,
            status: FragmentStatus
    ) -> FragmentTransaction:
        """
        Raises:

            IntegrityError - если при создании fragment_tx.fragment_id UUID будет неуникальным.
        """

        fragment_tx_kwargs: FragmentTransactionKwargs = {
            "fragment_id": fragment_tx_id,
            "id_from_payment_api": transaction_id,
            "status": status
        }

        return await self.model.objects.acreate(**fragment_tx_kwargs)

    async def get_by_fragment_id(self, fragment_tx_id: UUID) -> FragmentTransaction | None:
        return await self.model.objects.filter(fragment_id=fragment_tx_id).afirst()

    async def get_fragment_api_jwt_token(self) -> str:
        return (await self.model_api.aget_solo()).token

    async def update_status_by_id(self, fragment_tx_id: UUID, new_status: FragmentStatus) -> bool:
        update_fields: dict[str, object] = {
            "status": new_status
        }

        exclude_old_data = update_fields.copy()

        update_fields["updated_at"] = Case(When(status=new_status, then=F("updated_at")), default=Now())

        return (
                await self.model.objects
                .filter(fragment_id=fragment_tx_id)
                .exclude(**exclude_old_data)
                .aupdate(**update_fields) > 0
        )
