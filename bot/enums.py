from enum import StrEnum


class MainMenuAction(StrEnum):
    BUY = "buy"
    SUPPORT = "support"
    PROFILE = "profile"
    INFO = "info"


class ProfileAction(StrEnum):
    HISTORY = "history"
    REFERRALS = "referrals"


class BackDestination(StrEnum):
    MAIN_MENU = "main_menu"
    CHOOSE_QUANTITY = "choose_quantity"
    CUSTOM_QUANTITY_INPUT = "custom_quantity_input"
    CHOOSE_RECIPIENT = "choose_recipient"
    ENTER_GIFT_USERNAME = "enter_gift_username"
    CHOOSE_PAYMENT_SELF = "choose_payment_self"
    CHOOSE_PAYMENT_GIFT = "choose_payment_gift"
    PROFILE = "profile"
    REFERRALS_LIST = "referrals_list"