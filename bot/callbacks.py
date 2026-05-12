from typing import cast
from dataclasses import dataclass

from bot.enums import MainMenuAction, BackDestination, RecipientMode, ProfileAction


def cast_callback[C](callback: type[C], update_callback_query_data: str | None) -> C:
    return cast(C, update_callback_query_data)


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
