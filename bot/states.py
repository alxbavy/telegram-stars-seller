from enum import IntEnum, auto


class BotConversationState(IntEnum):
    MAIN_MENU = auto()  # UI 1
    SUPPORT = auto()  # UI 3

    CHOOSE_QUANTITY = auto()  # UI 2
    CUSTOM_QUANTITY_INPUT = auto()  # UI 5
    LARGE_ORDER_WARNING = auto()  # UI 6

    CHOOSE_RECIPIENT = auto()  # UI 4
    ENTER_GIFT_USERNAME = auto()  # UI 8
    USERNAME_NOT_FOUND = auto()  # UI 8b

    CHOOSE_PAYMENT_SELF = auto()  # UI 7
    CHOOSE_PAYMENT_GIFT = auto()  # UI 9

    ORDER_CONFIRMATION_SELF = auto()  # UI 10
    ORDER_CONFIRMATION_GIFT = auto()  # UI 11

    PROFILE = auto()  # UI 14
    ORDER_HISTORY = auto()  # UI 15
    REFERRALS_LIST = auto()  # UI 16
    REFERRAL_PURCHASES = auto()  # UI 17
