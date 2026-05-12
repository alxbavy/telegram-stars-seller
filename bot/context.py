from dataclasses import dataclass, field

from telegram import Message
from telegram.ext import ContextTypes

from bot.enums import RecipientMode

from core.dto.user import UserProfileDTO


@dataclass
class OrderDraft:
    quantity: int | None = None
    recipient_mode: RecipientMode | None = None
    target_username: str | None = None
    payment_method_id: str | None = None
    checkout_transaction_id: str | None = None
    checkout_url: str | None = None


@dataclass
class ListNavigationState:
    history_page: int = 1
    referrals_page: int = 1
    referral_purchases_page: int = 1
    referral_user_id: int | None = None


@dataclass
class ViewContext:
    active_conversation: Message | None = None
    order: OrderDraft = field(default_factory=OrderDraft)
    lists: ListNavigationState = field(default_factory=ListNavigationState)
    profile_data: UserProfileDTO | None = None

def get_view_context(context: ContextTypes.DEFAULT_TYPE) -> ViewContext:
    """Helper для безопасного получения/создания контекста."""
    if "view_context" not in context.user_data:
        context.user_data["view_context"] = ViewContext()
    return context.user_data["view_context"]

def clear_order_draft(context: ContextTypes.DEFAULT_TYPE):
    """Очистка черновика заказа."""
    ctx = get_view_context(context)
    ctx.order = OrderDraft()
