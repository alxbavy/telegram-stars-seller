from dataclasses import dataclass


@dataclass(frozen=True)
class OrderHistoryItemDTO:
    date: str
    stars: int
    price: float


@dataclass(frozen=True)
class OrderHistoryPageDTO:
    items: list[OrderHistoryItemDTO]
    current_page: int
    total_pages: int