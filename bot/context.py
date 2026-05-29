from dataclasses import dataclass, field, asdict

from dacite import from_dict

from telegram import Message
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from bot.enums import RecipientMode

from core.dto.user import UserProfileDTO


@dataclass
class OrderDraft:
    quantity: int | None = None
    recipient_mode: RecipientMode | None = None
    target_username: str = ""
    payment_method: str | None = None
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
    temporary_messages: list[tuple[int, int]] = field(default_factory=list)


def get_view_context(context: ContextTypes.DEFAULT_TYPE) -> ViewContext:
    """Helper для безопасного получения/создания контекста."""
    if "view_context" not in context.user_data:
        context.user_data["view_context"] = ViewContext()
    # else:  TODO: раскомментировать в релизе, в дебаге персистентность мешает
    #     context.user_data["view_context"] = from_dict(ViewContext, data=asdict(context.user_data["view_context"]))
    return context.user_data["view_context"]


def clear_context(context: ContextTypes.DEFAULT_TYPE):
    """Очистка черновика заказа."""
    context.user_data["view_context"] = ViewContext()


def clear_profile_data(context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)
    ctx.profile_data = None


def add_temporary_message(context: ContextTypes.DEFAULT_TYPE, msg: Message):
    ctx = get_view_context(context)
    ctx.temporary_messages.append((msg.chat_id, msg.message_id))


async def clear_temporary_messages(context: ContextTypes.DEFAULT_TYPE):
    ctx = get_view_context(context)
    for chat_id, message_id in ctx.temporary_messages:
        try:
            _ = await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except BadRequest:
            pass
    ctx.temporary_messages = []
