from core.dto.stats import OrderHistoryPageDTO, OrderHistoryItemDTO
from core.repositories.transaction import TransactionRepository


class StatsService:
    def __init__(self, trans_repo: TransactionRepository):
        self._trans_repo = trans_repo

    async def get_order_history(self, user_id: int, page: int, per_page: int = 5) -> OrderHistoryPageDTO:
        """
        Возвращает список успешных заказов для страницы и общее количество страниц.
        """
        all_transactions = await self._trans_repo.get_many_success_by_telegram_id(user_id)

        total_count = len(all_transactions)
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        if page > total_pages: page = total_pages
        if page < 1: page = 1

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_items = all_transactions[start_idx:end_idx]

        items_dto = [
            OrderHistoryItemDTO(
                date=item.created_at.strftime("%d.%m.%Y"),
                stars=item.amount_stars,
                price=float(item.amount_fiat)
            )
            for item in page_items
        ]

        return OrderHistoryPageDTO(
            items=items_dto,
            current_page=page,
            total_pages=total_pages
        )
