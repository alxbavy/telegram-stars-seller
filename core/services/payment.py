import json
import logging
from collections.abc import Mapping
from decimal import Decimal
from typing import final
from uuid import UUID

from django.utils.timezone import datetime, timedelta

from core.dto.payment import PaymentDTO, PaymentMethodDTO
from core.integrations.fragment.schemas import SendStarsResponse
from core.integrations.platega.client import PlategaClient
from core.integrations.platega.schemas import PaymentPayloadDict, PlategaWebhookRequestJson
from core.models import Transaction, TARGET_SELF
from core.repositories.transaction import TransactionRepository
from core.repositories.user import UserRepository
from core.repositories.payment import PaymentRepository

from core.domain.enums import TransactionStatus
from core.services.star_price import StarService
from core.integrations.fragment.client import FragmentClient
from core.services.user import UnregisteredUser


logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("payment_audit")


class NoUsernameError(Exception):
    """Исключение для случая, когда username отсутствует."""


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
            platega_client: PlategaClient,
            fragment_client: FragmentClient
    ):
        self._trans_repo = trans_repo
        self._user_repo = user_repo
        self._payment_repo = payment_repo
        self._star_service = star_service
        self._platega_client = platega_client
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
            user_id: int, message_id: int,
            price: Decimal, stars_count: int, payment_api: str, method: int | str,
            target_username: str = ""
    ) -> PaymentDTO:
        """
        Обращается к внешнему API для создания платежа и получении ссылки на оплату, потом сохраняет транзакцию в БД.

        Возвращает PaymentDTO:

        `transaction_id` - UUID

        `pay_url` - str

        `price` - Decimal

        `expires_in` - str

        Arguments:

        - `user_id` - int, Telegram ID.

        - `message_id` - int, ID сообщения, для которого генерируется ссылка на оплату, чтобы вебхук мог изменить
        это сообщение.

        - `price` - Decimal, цена покупки.

        - `stars_count` - int, кол-во звёзд для перевода.

        - `payment_api` - str, API для создания платежа.

        - `method` - int | str, если payment_api = "Platega", то это должен быть int, который соответствует
        нужному методу, другие API сейчас не поддерживаются.
        Значения для int: 2 - СБП, 11 - Карточный эквайринг, 12 - Международный эквайринг, 13 - Криптовалюта.
        В данный момент поддерживается только RUB.

        - `target_username` - str, по умолчанию "", если указан, то этому человеку будет сделан перевод звёзд.
        """

        user_buyer = await self._user_repo.get_by_telegram_id(user_id)
        if user_buyer is None:
            raise UnregisteredUser(user_id)

        payload_target_username = None
        if not target_username:
            if not user_buyer.username:
                raise NoUsernameError()

            payload_target_username = user_buyer.username

        if "platega" in payment_api.lower():
            description = f"TgId:{user_id}\nUserId:{user_id}"
            if payload_target_username is None:
                payload_target_username = target_username
            payload: PaymentPayloadDict = {
                "user_id": user_id,
                "message_id": message_id,
                "price": float(price),
                "stars_count": stars_count,
                "target_username": payload_target_username,
            }
            payment_dto = await self._platega_client.create_payment( # TODO: протестировать клиент платеги
                int(method),
                float(price), "RUB",
                description,
                payload=json.dumps(payload, ensure_ascii=False)
            )
        else:
            raise NotImplementedError("Only Platega API is supported now")

        _ = await self._trans_repo.create_transaction(
            transaction_id=payment_dto.transaction_id,
            user=user_buyer,
            amount_fiat=float(payment_dto.price),
            amount_stars=stars_count,
            payment_method=f"{payment_api} - {method}",
            expires_in=payment_dto.expires_in,
            target_username=target_username
        )

        return payment_dto

    async def create_transaction(
            self,
            transaction_id: str, user_id: int,
            price: float, stars_count: int,
            payment_api: str, method: str,
            target_username: str = "",
            status: str = TransactionStatus.PENDING, payload: Mapping[str, object] | None = None
    ) -> Transaction:
        """
        Создаёт транзакцию с нуля. Должно вызываться в вебхуке, если по какой-то причине транзакция отсутствует в БД.
        """
        transaction_uuid = UUID(transaction_id)

        transaction = await self._trans_repo.get_by_transaction_id(transaction_uuid)
        if transaction:
            return transaction

        telegram_user = await self._user_repo.get_by_telegram_id(user_id)
        if telegram_user is None:
            raise UnregisteredUser(user_id)

        return await self._trans_repo.create_transaction(
            transaction_id=transaction_uuid,
            user=telegram_user,
            amount_fiat=price,
            amount_stars=stars_count,
            payment_method=f"{payment_api} - {method}",
            target_username=target_username,
            status=status,
            json_payload=payload
        )

    async def get_transaction_by_uuid(
            self,
            transaction_uuid: UUID,
            data: PlategaWebhookRequestJson, payload: PaymentPayloadDict | None
    ) -> Transaction | None:
        transaction = None
        try:
            transaction = await self._trans_repo.get_by_transaction_id(transaction_uuid)
        except Exception as db_err:
            logger.exception(f"DB error when trying to get transaction {transaction_uuid}\n{db_err =}")

        if transaction is None:
            if payload is None:
                return None

            target_username = payload["target_username"]
            try:
                telegram_user = await self._user_repo.get_by_telegram_id(payload["user_id"])
                if telegram_user and telegram_user.username == payload["target_username"]:
                    target_username = ""  # Пустое значение, чтобы использовалось TARGET_SELF
            except Exception as db_err:
                logger.exception(f"DB error when trying to get user for creating transaction {transaction_uuid}\n{db_err =}")

            try:
                transaction = await self.create_transaction(
                    transaction_id=str(transaction_uuid),
                    user_id=payload["user_id"],
                    price=data["amount"],
                    stars_count=payload["stars_count"],
                    payment_api="Platega (Generated)",
                    method=str(data["paymentMethod"]),
                    target_username=target_username,
                    payload=data
                )
            except Exception as transaction_err:
                logger.exception(f"DB error when trying to create transaction in webhook\n{transaction_err = }")
                return None

        return transaction

    async def confirm_payment(self, transaction: Transaction) -> Transaction | TransactionStatus:
        """
        Вызывается при получении Вебхука от платежки.

        - Если `transaction.status == "SUCCESS"`, то сразу вернётся соответствующая транзакция.

        - Если перевод звёзд пройдёт успешно, то `transaction.status` станет `"SUCCESS"`, при неудачном переводе -
        `"FAILED"`.

        - Если при переводе звёзд возникнет ошибка, то `transaction.status` сам станет `"FAILED"`, и вернётся транзакция.

        - Если по какой-то причине БД будет недоступна, вернётся статус транзакции - SUCCESS при успехе,
        FAILED в любом другом случае.
        """

        if transaction.status == TransactionStatus.SUCCESS:
            return transaction

        try:
            target_username = transaction.target_username
            if transaction.target_username == TARGET_SELF:
                target_username = transaction.telegram_user.username
            response: SendStarsResponse = await self._fragment_client.send_stars(
                target_username, transaction.amount_stars
            )
        except Exception as request_err:
            logger.exception(f"Error when sending stars for transaction {transaction.id}\n{request_err = }")
            try:
                transaction = await self._trans_repo.update_payload(
                    transaction,
                    {"error_msg": str(request_err)}
                )
                transaction = await self._trans_repo.update_status(
                    transaction,
                    TransactionStatus.FAILED
                )
                return transaction
            except Exception as db_err:
                logger.exception(f"DB error with transaction {transaction.id} when trying to log error\n{db_err = }")
                return TransactionStatus.FAILED

        is_success = response["success"]
        if is_success:
            audit_logger.info(f"Transaction {transaction.id} is succeeded")

        new_status = TransactionStatus.SUCCESS if is_success else TransactionStatus.FAILED
        try:
            transaction = await self._trans_repo.update_payload(transaction, response)
            return await self._trans_repo.update_status(transaction, new_status)

        except Exception as db_err:
            logger.exception(f"DB error with transaction {transaction.id} when trying to set {new_status}\n{db_err = }")
            return new_status

    async def cancel_transaction(
            self,
            transaction: Transaction,
            payload: Mapping[str, object] | None = None
    ) -> Transaction | TransactionStatus:
        """
        Выставляет транзакции статус `"CANCELLED"`, если её статус не был `"SUCCESS"`.

        - Если БД по какой-то причине недоступно, вернётся статус транзакции.
        """

        try:
            if payload is not None:
                transaction = await self._trans_repo.update_payload(transaction, payload)
        except Exception as db_err:
            logger.exception(f"DB error with transaction {transaction.id} when trying to log cancelling payment\n{db_err = }")

        try:
            return (
                await self._trans_repo.update_status(transaction, TransactionStatus.CANCELLED)
                if transaction.status != TransactionStatus.SUCCESS
                else transaction
            )

        except Exception as db_err:
            logger.exception(f"DB error with transaction {transaction.id} when trying to cancel payment\n{db_err = }")
            return TransactionStatus.CANCELLED

    async def delete_expired_transactions(self) -> None:
        """Удаляет все транзакции со статусом PENDING, у которых истекло время ожидания."""
        await self._trans_repo.delete_expired_transactions(None)

    # Deprecated:
    # Удаление отдельных транзакций по таймеру небезопасно и неэффективно,
    # лучше использовать self.delete_expired_transactions
    async def delete_transactions_expires_in(self, expires_in: str, transaction_ids: list[UUID] | UUID | None = None) -> None:
        """
        Удаляет транзакции (или одну) со статусом PENDING, у которых истекло время ожидания.

        Arguments:

        - `expires_in` - имеет формат HH:MM:SS (%H:%M:%S в datetime).

        - `transaction_ids` - list[UUID] | UUID | None, если указано, то удалит либо транзакции с указанными ID,
        либо конкретную транзакцию, иначе удалит все найденные транзакции (в каждом случае проверяется
        статус PENDING и время жизни).
        """
        expires_in_td = datetime.strptime(expires_in, "%H:%M:%S")
        expires_in_td = timedelta(
            hours=expires_in_td.hour,
            minutes=expires_in_td.minute,
            seconds=expires_in_td.second
        )
        await self._trans_repo.delete_expired_transactions(expires_in_td, transaction_ids)

    async def _get_provider_link(self, order_id: str, amount: Decimal, method: str) -> str:
        """
        В данный момент просто заглушка.

        Интеграция с API платежных систем.
        """
        return f"https://test.link/pay/{order_id}?amount={amount}"
