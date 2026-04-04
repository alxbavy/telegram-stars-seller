from dataclasses import dataclass
from enum import StrEnum
from typing import Optional
from .context import RecipientMode


class MainMenuAction(StrEnum):
    BUY = "buy"
    SUPPORT = "support"
    PROFILE = "profile"

class ProfileAction(StrEnum):
    HISTORY = "history"
    REFERRALS = "referrals"

class BackDestination(StrEnum):
    MAIN_MENU = "main_menu"
    CHOOSE_QUANTITY = "choose_quantity"
    CUSTOM_QUANTITY_INPUT = "custom_quantity_input"
    CHOOSE_RECIPIENT = "choose_recipient"
    ENTER_GIFT_USERNAME = "enter_gift_username"
    PROFILE = "profile"
    REFERRALS_LIST = "referrals_list"


@dataclass(frozen=True)
class MainMenuCallback:
    action: MainMenuAction

@dataclass(frozen=True)
class BackCallback:
    destination: BackDestination

@dataclass(frozen=True)
class FixedQuantityCallback:
    amount: int

@dataclass(frozen=True)
class CustomQuantityCallback:
    pass

@dataclass(frozen=True)
class RecipientModeCallback:
    mode: RecipientMode

@dataclass(frozen=True)
class PaymentMethodCallback:
    method_id: str

@dataclass(frozen=True)
class ConfirmOrderCallback:
    pass

@dataclass(frozen=True)
class ProfileMenuCallback:
    action: ProfileAction

@dataclass(frozen=True)
class HistoryPageCallback:
    page: int

@dataclass(frozen=True)
class ReferralsPageCallback:
    page: int

@dataclass(frozen=True)
class ReferralDetailsCallback:
    ref_user_id: int
    page: int = 1

@dataclass(frozen=True)
class ReferralPurchasesPageCallback:
    ref_user_id: int
    page: int

@dataclass(frozen=True)
class RepeatOrderCallback:
    pass
