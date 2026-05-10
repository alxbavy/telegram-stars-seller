from core.domain.enums import TransactionStatus
from core.dto.stats import OrderHistoryPageDTO, OrderHistoryItemDTO
from core.repositories.transaction import TransactionRepository


class StatsService:
    def __init__(self, trans_repo: TransactionRepository):
        self._trans_repo = trans_repo

    async def get_order_history(self, user_id: int, page: int, per_page: int = 5) -> OrderHistoryPageDTO:
        """
        Возвращает список успешных заказов для страницы и общее количество страниц.
        """
        if page < 1:
            raise ValueError("page must be greater than 1")

        transactions = await self._trans_repo.get_many_by(
            telegram_id=user_id,
            status=TransactionStatus.SUCCESS,
            start_idx=per_page * (page - 1),
            stop_idx=per_page * page,
        )

        if not transactions:
            return OrderHistoryPageDTO(
                items=[],
                current_page=page,
                total_pages=1
            )

        items_dto = [
            OrderHistoryItemDTO(
                date=transaction.created_at.strftime("%d.%m.%Y"),
                stars=transaction.amount_stars,
                price=float(transaction.amount_fiat)
            )
            for transaction in transactions
        ]

        total_transactions_count: int = await self._trans_repo.get_many_by(
            telegram_id=user_id,
            status=TransactionStatus.SUCCESS,
            is_count_only=True,
        )
        total_pages: int = total_transactions_count // per_page + 1

        return OrderHistoryPageDTO(
            items=items_dto,
            current_page=page,
            total_pages=total_pages
        )
