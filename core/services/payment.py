from decimal import Decimal
from typing import final
from uuid import UUID

from core.dto.payment import PaymentDTO, PaymentMethodDTO
from core.repositories.transaction import TransactionRepository
from core.repositories.user import UserRepository
from core.repositories.payment import PaymentRepository

from core.domain.enums import TransactionStatus
from core.services.star_price import StarService
from core.integrations.fragment import FragmentClient

class MaintenanceModeException(Exception):
    """Исключение для технического перерыва."""


@final
class PaymentService:
    def __init__(
            self,
            trans_repo: TransactionRepository,
            user_repo: UserRepository,
            payment_repo: PaymentRepository,
            star_service: StarService,
            fragment_client: FragmentClient
    ):
        self._trans_repo = trans_repo
        self._user_repo = user_repo
        self._payment_repo = payment_repo
        self._star_service = star_service
        self._fragment_client = fragment_client

    async def ensure_no_maintenance_mode(self) -> None:
        if await self._payment_repo.is_maintenance_mode():
            raise MaintenanceModeException("maintenance_mode on True")

    async def get_active_payment_methods(self) -> tuple[PaymentMethodDTO, ...]:
        return tuple(
            PaymentMethodDTO(
                api_name=method.api.name,
                name=method.name,
                external_id=method.external_id,
                commission_percent=method.commission_percent
            )
            for method in await self._payment_repo.get_many_by()
        )

    async def create_payment_and_transaction(
            self,
            user_id: int,
            stars_count: int,
            method: str,
            target_username: str | None = None
    ) -> PaymentDTO:
        """
        Создает заказ, сохраняет транзакцию в БД и генерирует ссылку на оплату.
        """

        price = await self._star_service.get_order_price(stars_count, method)

        user_buyer = await self._user_repo.get_by_telegram_id(user_id)
        transaction = await self._trans_repo.create_transaction(  # TODO: id приходит из платеги
            user=user_buyer,
            amount_fiat=price,
            amount_stars=stars_count,
            payment_method=method,
            target_username=target_username
        )

        pay_url = await self._get_provider_link(transaction.id, price, method)

        return PaymentDTO(
            transaction_id=transaction.id,
            pay_url=pay_url,
            price=price
        )

    async def confirm_payment(self, transaction_id: str):
        """
        Вызывается при получении Вебхука от платежки.
        """
        # TODO: Должно вызываться не только при получении Вебхука от платежки,
        #       но и из списка транзакции, когда перевод не прошёл по вине FragmentAPI
        #       (либо пользователь должен связаться с поддержкой, чтобы перевод был совершён вручную)
        transaction = await self._trans_repo.get_by_transaction_id(transaction_id)
        if transaction and transaction.status == TransactionStatus.PENDING:
            is_send_success, payload = await self._fragment_client.send_stars(
                transaction.telegram_user.username, transaction.amount_stars
            )

            if is_send_success:
                new_transaction_status = TransactionStatus.SUCCESS
            else:
                new_transaction_status = TransactionStatus.FAILED
                await self._trans_repo.update_payload(transaction, payload)
            await self._trans_repo.update_status(transaction, new_transaction_status)

            return transaction

        return None

    async def delete_transactions(self, expires_in: str, transaction_ids: list[UUID] | UUID | None = None) -> None:
        """
        `expires_in` - имеет формат HH:MM:SS (%H:%M:%S в datetime)
        """
        ...

    async def _get_provider_link(self, order_id: str, amount: Decimal, method: str) -> str:
        """
        Интеграция с API платежных систем.
        """
        return f"https://test.link/pay/{order_id}?amount={amount}"
