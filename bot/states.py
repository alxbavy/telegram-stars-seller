from enum import StrEnum, auto


class BotConversationState(StrEnum):
    # auto() - использует название переменной в нижнем регистре
    # При персистентности старые названия не должны просто удаляться, а должны как-то обрабатываться

    MAIN_MENU = auto()
    SUPPORT = auto()
    PROFILE = auto()
    INFO = auto()
    ORDER_HISTORY = auto()

    CHOOSE_QUANTITY = auto()
    CUSTOM_QUANTITY_INPUT = auto()

    CHOOSE_RECIPIENT = auto()
    ENTER_GIFT_USERNAME = auto()

    CHOOSE_PAYMENT = auto()
    ENTER_PROMO = auto()

    ORDER_CONFIRMATION = auto()
    ORDER_CONFIRMED = auto()

    LARGE_ORDER_WARNING = auto()
    USERNAME_NOT_FOUND = auto()
