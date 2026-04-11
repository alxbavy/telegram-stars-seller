from decimal import Decimal

from core.repositories.transaction import TransactionRepository
from core.repositories.user import UserRepository
from core.repositories.payment import PaymentRepository

from core.domain.enums import TransactionStatus
from core.schemas.payment import PaymentDTO
from core.services.star_price import StarService
from core.integrations.fragment import FragmentClient


class PaymentService:
    '''def __init__(
            self,
            trans_repo,
            user_repo
            payment_repo,
            star_service: StarService,
            fragment_client: FragmentClient
    ):
        self._trans_repo = trans_repo
        self._user_repo = user_repo
        self._payment_repo = payment_repo
        self._star_service = star_service
        self._fragment_client = fragment_client'''

    async def create_checkout(
            self,
            user_id: int,
            stars_count: int,
            method: str,
            target_username: str = None
    ) -> PaymentDTO:
        """
        Создает заказ, сохраняет транзакцию в БД и генерирует ссылку на оплату.
        """
        if await self._payment_repo.is_maintenance_mode():
            raise Exception("maintenance_mode on True")

        amount = await self._star_service.get_order_price(stars_count, method)

        user_buyer = await self._user_repo.get_by_telegram_id(user_id)
        transaction = await self._trans_repo.create_transaction(
            user=user_buyer,
            amount_fiat=amount,
            amount_stars=stars_count,
            payment_method=method,
            target_username=target_username
        )

        pay_url = await self._get_provider_link(transaction.id, amount, method)

        return PaymentDTO(
            transaction_id=transaction.id,
            pay_url=pay_url,
            amount=amount
        )

    async def _get_provider_link(self, order_id: str, amount: Decimal, method: str) -> str:
        """
        Интеграция с API платежных систем.
        """
        return f"https://test.link/pay/{order_id}?amount={amount}"

    async def confirm_payment(self, transaction_id: str):
        """
        Вызывается при получении Вебхука от платежки.
        """
        # TODO: Должно вызываться не только при получении Вебхука от платежки,
        # TODO: но и из списка транзакции, когда перевод не прошёл по вине FragmentAPI
        # TODO: (либо пользователь должен связаться с поддержкой, чтобы перевод был совершён вручную)
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
