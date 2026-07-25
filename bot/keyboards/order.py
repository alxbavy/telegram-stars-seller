from decimal import Decimal
from collections.abc import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import (
    create_callback,
    FixedQuantityCallback, CustomQuantityCallback, BackCallback,
    RecipientModeCallback, PaymentMethodCallback, PromoCodeCallback,
    OrderConfirmedCallback
)
from bot.enums import BackDestination, RecipientMode

from core.dto.payment import PaymentMethodDTO


async def build_quantity_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⭐ 50 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(50))
            ),
            InlineKeyboardButton(
                "⭐ 100 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(100))
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 250 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(250))
            ),
            InlineKeyboardButton(
                "⭐ 300 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(300))
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ 500 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(500))
            ),
            InlineKeyboardButton(
                "⭐ 1000 звёзд",
                callback_data=await create_callback(telegram_id, FixedQuantityCallback(1000))
            )
        ],
        [InlineKeyboardButton(
            "✏️ Своё количество",
            callback_data=await create_callback(telegram_id, CustomQuantityCallback())
        )],
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.MAIN_MENU))
        )]
    ])


async def build_back_to_quantity_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.CHOOSE_QUANTITY))
        )]])


async def build_large_order_kb(telegram_id: int, support_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Связаться с поддержкой", url=support_url)],
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.CUSTOM_QUANTITY_INPUT))
        )]
    ])


async def build_recipient_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🥰 Себе",
            callback_data=await create_callback(telegram_id, RecipientModeCallback(RecipientMode.SELF))
        )],
        [InlineKeyboardButton(
            "🎁 В подарок",
            callback_data=await create_callback(telegram_id, RecipientModeCallback(RecipientMode.GIFT))
        )],
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.CHOOSE_QUANTITY))
        )]
    ])


async def build_back_to_recipient_kb(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(BackDestination.CHOOSE_RECIPIENT))
        )]
    ])


async def build_payment_methods_kb(
        telegram_id: int,
        payment_methods_with_prices: Iterable[tuple[PaymentMethodDTO, Decimal]],
        back_dest: BackDestination
) -> InlineKeyboardMarkup:
    kb: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(
            "🎟️ Ввести промокод",
            callback_data=await create_callback(telegram_id, PromoCodeCallback())
        )]
    ]

    kb.extend([
        [InlineKeyboardButton(
            f"{method.name} — {price} ₽",
            callback_data=await create_callback(telegram_id, PaymentMethodCallback(
                method_api=method.api_name,
                method=method.name,
                method_external_id=method.external_id,
                price=price
            ))
        )] for method, price in payment_methods_with_prices
    ])

    kb.append([InlineKeyboardButton(
        "◀️ Назад",
        callback_data=await create_callback(telegram_id, BackCallback(back_dest))
    )])

    return InlineKeyboardMarkup(kb)


async def build_order_confirmation_kb(telegram_id: int, back_dest: BackDestination) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "📦 Создать заказ!",
            callback_data=await create_callback(telegram_id, OrderConfirmedCallback())
        )],
        [InlineKeyboardButton(
            "◀️ Назад",
            callback_data=await create_callback(telegram_id, BackCallback(back_dest))
        )],
    ])


def build_order_confirmed_kb(pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💳 Оплатить", url=pay_url)]])
