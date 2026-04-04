from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional
from telegram.ext import ContextTypes

class RecipientMode(StrEnum):
    SELF = "self"
    GIFT = "gift"

@dataclass
class OrderDraft:
    quantity: Optional[int] = None
    recipient_mode: Optional[RecipientMode] = None
    target_username: Optional[str] = None
    payment_method_id: Optional[str] = None
    checkout_transaction_id: Optional[str] = None
    checkout_url: Optional[str] = None

@dataclass
class ListNavigationState:
    history_page: int = 1
    referrals_page: int = 1
    referral_purchases_page: int = 1
    referral_user_id: Optional[int] = None

@dataclass
class ViewContext:
    order: OrderDraft = field(default_factory=OrderDraft)
    lists: ListNavigationState = field(default_factory=ListNavigationState)

def get_view_context(context: ContextTypes.DEFAULT_TYPE) -> ViewContext:
    """Helper для безопасного получения/создания контекста."""
    if "view_context" not in context.user_data:
        context.user_data["view_context"] = ViewContext()
    return context.user_data["view_context"]

def clear_order_draft(context: ContextTypes.DEFAULT_TYPE):
    """Очистка черновика заказа."""
    ctx = get_view_context(context)
    ctx.order = OrderDraft()
