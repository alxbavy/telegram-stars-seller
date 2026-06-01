from enum import IntEnum, auto


class BotConversationState(IntEnum):
    MAIN_MENU = auto()
    SUPPORT = auto()
    PROFILE = auto()
    INFO = auto()

    CHOOSE_QUANTITY = auto()
    CUSTOM_QUANTITY_INPUT = auto()
    CHOOSE_RECIPIENT = auto()
    ENTER_GIFT_USERNAME = auto()
    CHOOSE_PAYMENT_SELF = auto()
    CHOOSE_PAYMENT_GIFT = auto()
    ORDER_CONFIRMATION_SELF = auto()
    ORDER_CONFIRMATION_GIFT = auto()
    ORDER_HISTORY = auto()

    LARGE_ORDER_WARNING = auto()
    USERNAME_NOT_FOUND = auto()
