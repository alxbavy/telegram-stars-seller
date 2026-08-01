from enum import StrEnum


class MainMenuAction(StrEnum):
    BUY = "buy"
    SUPPORT = "support"
    PROFILE = "profile"
    INFO = "info"


class ProfileAction(StrEnum):
    HISTORY = "history"
    REFERRALS = "referrals"


class RecipientMode(StrEnum):
    SELF = "self"
    GIFT = "gift"


class BackDestination(StrEnum):
    MAIN_MENU = "main_menu"
    CHOOSE_QUANTITY = "choose_quantity"
    CUSTOM_QUANTITY_INPUT = "custom_quantity_input"
    CHOOSE_RECIPIENT = "choose_recipient"
    ENTER_GIFT_USERNAME = "enter_gift_username"
    CHOOSE_PAYMENT = "choose_payment"
    ENTER_PROMO = "enter_promo"
    ORDER_CONFIRMATION = "order_confirmation"
    PROFILE = "profile"
    REFERRALS_LIST = "referrals_list"
