from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import (
    FixedQuantityCallback, CustomQuantityCallback, BackCallback,
    RecipientModeCallback, PaymentMethodCallback, PromoCodeCallback, OrderConfirmedCallback, RepeatOrderCallback
)
from bot.enums import BackDestination, RecipientMode
from core.models import PromoCode

from core.repositories.utils import db_action_with_tenacity
from core.services.payment import PaymentService
from core.services.star_price import StarService


def build_quantity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ 50 звёзд", callback_data=FixedQuantityCallback(50)),
            InlineKeyboardButton("⭐ 100 звёзд", callback_data=FixedQuantityCallback(100))
        ],
        [
            InlineKeyboardButton("⭐ 250 звёзд", callback_data=FixedQuantityCallback(250)),
            InlineKeyboardButton("⭐ 300 звёзд", callback_data=FixedQuantityCallback(300))
        ],
        [
            InlineKeyboardButton("⭐ 500 звёзд", callback_data=FixedQuantityCallback(500)),
            InlineKeyboardButton("⭐ 1000 звёзд", callback_data=FixedQuantityCallback(1000))
        ],
        [InlineKeyboardButton("✏️ Своё количество", callback_data=CustomQuantityCallback())],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.MAIN_MENU))]
    ])


def build_back_to_quantity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_QUANTITY))]])


def build_large_order_kb(support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CUSTOM_QUANTITY_INPUT))]
    ])


def build_recipient_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥰 Себе", callback_data=RecipientModeCallback(RecipientMode.SELF))],
        [InlineKeyboardButton("🎁 В подарок", callback_data=RecipientModeCallback(RecipientMode.GIFT))],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_QUANTITY))]
    ])


def build_back_to_recipient_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_RECIPIENT))]])


def build_user_not_found_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Ввести снова", callback_data=BackCallback(BackDestination.ENTER_GIFT_USERNAME))],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(BackDestination.CHOOSE_RECIPIENT))]
    ])


def build_payment_methods_kb_static(sbp_price: Decimal, card_price: Decimal, back_dest: BackDestination) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📲 СБП — {sbp_price} ₽", callback_data=PaymentMethodCallback(
            method_api="",
            method="sbp",
            method_external_id="",
            commission_percent=Decimal("5.00"),
            price=None
        ))],
        [InlineKeyboardButton(f"💳 Картой — {card_price} ₽", callback_data=PaymentMethodCallback(
            method_api="",
            method="card",
            method_external_id="",
            commission_percent=Decimal("10.00"),
            price=None
        ))],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))]
    ])


# TODO: рефакторинг - можно вынести сервисы в хэндлер, и передавать сюда payment_methods_with_prices: dict
async def build_payment_methods_kb_dynamic(
        stars_count: int,
        payment_service: PaymentService, star_service: StarService,
        promo: PromoCode | None,
        back_dest: BackDestination
) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton("🎟️ Ввести промокод", callback_data=PromoCodeCallback())]
    ]

    payment_methods = await db_action_with_tenacity(payment_service.get_active_payment_methods())
    for method in payment_methods:

        emoji = ""
        if "сбп" in method.name.lower():
            emoji = "📲 "
        elif any(word in method.name.lower() for word in ["карта", "картой", "эквайринг"]):
            emoji = "💳 "
        text = method.name

        price = await db_action_with_tenacity(
            star_service.get_order_price(stars_count, method.commission_percent)
        )
        display_price = price
        if promo is not None:
            display_price = price * (1 - promo.discount / 100)

        kb.append([InlineKeyboardButton(f"{emoji}{text} — {display_price} ₽", callback_data=PaymentMethodCallback(
            method_api=method.api_name,
            method=method.name,
            method_external_id=method.external_id,
            price=price,
            commission_percent=None
        ))])
    kb.append([InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))])

    return InlineKeyboardMarkup(kb)


def build_order_confirmation_kb(back_dest: BackDestination) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Создать заказ!", callback_data=OrderConfirmedCallback())],
        [InlineKeyboardButton("◀️ Назад", callback_data=BackCallback(back_dest))],
    ])


def build_order_confirmed_kb(pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💳 Оплатить", url=pay_url)]])


def build_repeat_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✨ Сделать ещё заказ!", callback_data="repeat_order")]])
