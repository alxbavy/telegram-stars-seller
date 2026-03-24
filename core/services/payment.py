import uuid
from decimal import Decimal
from core.repositories.trans_repo import TransactionRepository
from core.repositories.settings_repo import SettingsRepository

from core.schemas.payment import PaymentDTO
from core.services.star_service import StarService


class PaymentService:
    def __init__(
            self,
            trans_repo: TransactionRepository,
            settings_repo: SettingsRepository,
            star_service: StarService
    ):
        self._trans_repo = trans_repo
        self._settings_repo = settings_repo
        self._star_service = star_service

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
        settings = self._settings_repo.get_active_settings()
        if settings.maintenance_mode:
            raise Exception("maintenance_mode on True")

        amount = await self._star_service.get_order_price(stars_count, method)

        order_id = str(uuid.uuid4())
        transaction = self._trans_repo.create_transaction(
            user_id=user_id,
            external_id=order_id,
            amount_fiat=amount,
            amount_stars=stars_count,
            payment_method=method,
            target_username=target_username,
            status="PENDING"
        )

        pay_url = await self._get_provider_link(order_id, amount, method)

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

    async def confirm_payment(self, external_id: str):
        """
        Вызывается при получении Вебхука от платежки.
        """
        transaction = self._trans_repo.get_by_external_id(external_id)
        if transaction and transaction.status == "PENDING":
            self._trans_repo.update_status(transaction.id, "SUCCESS")

            # TODO: Логика начисления звёзд

            return transaction
        return None