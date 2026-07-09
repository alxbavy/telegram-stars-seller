from enum import IntEnum, auto


# TODO: при реализации персистентности auto() надо заменить на конкретные числа
class BotConversationState(IntEnum):
    MAIN_MENU = auto()
    SUPPORT = auto()
    PROFILE = auto()
    INFO = auto()
    ORDER_HISTORY = auto()

    CHOOSE_QUANTITY = auto()
    CUSTOM_QUANTITY_INPUT = auto()

    CHOOSE_RECIPIENT = auto()
    ENTER_GIFT_USERNAME = auto()

    CHOOSE_PAYMENT_SELF = auto()
    CHOOSE_PAYMENT_GIFT = auto()

    ENTER_PROMO = auto()

    ORDER_CONFIRMATION_SELF = auto()
    ORDER_CONFIRMATION_GIFT = auto()

    ORDER_CONFIRMED = auto()

    LARGE_ORDER_WARNING = auto()
    USERNAME_NOT_FOUND = auto()
