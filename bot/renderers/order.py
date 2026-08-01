from decimal import Decimal
from uuid import UUID
from typing import overload

from telegram import Update, Message
from telegram.ext import ContextTypes

from bot.keyboards.main import build_back_to_main_menu_kb
from bot.keyboards.order import (
    build_quantity_kb,
    build_back_to_quantity_kb,
    build_large_order_kb,
    build_recipient_kb,
    build_back_to_recipient_kb,
    build_payment_methods_kb,
    build_order_confirmation_kb, build_order_confirmed_kb
)
from bot.middlewares.payment_method import get_payment_methods_with_prices
from bot.renderers.base import render_screen, send_new_message, update_existing_message

from bot.utils.active_conversation import autosave_active_conversation
from bot.utils.string_helpers import WordCase, get_ending_for_digit_string
from bot.enums import BackDestination

from core.models import TARGET_SELF, PromoCode


@overload
async def show_choose_quantity(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        is_send_new_message: bool = False
) -> Message: ...

@autosave_active_conversation
async def show_choose_quantity(update: Update, is_send_new_message: bool = False) -> Message:
    text = (
        "🧠 <b>Сколько покупаем звёзд?</b>\n\nПоказываем самые популярные варианты.\n"
        "Можно ввести своё количество ;)"
    )
    if not is_send_new_message:
        send_method = render_screen
    else:
        send_method = send_new_message

    return await send_method(
        update, text,
        reply_markup=await build_quantity_kb(update.effective_user.id),
        photo_name="choose_quantity.jpg"
    )


@autosave_active_conversation
async def show_custom_quantity_input(update: Update) -> Message:
    text = "🌟 <b>Введи количество звёзд</b>\n\nМинимум 50"
    return await render_screen(
        update, text,
        reply_markup=await build_back_to_quantity_kb(update.effective_user.id),
        photo_name=None
    )


async def send_small_order_error(update: Update) -> Message:
    text = (
        f"❌ <b>Ошибка! Можно купить минимум 50 звёзд!</b>\n"
        f"Вводи заново"
    )
    return await send_new_message(update, text, reply_markup=None, photo_name=None)


@autosave_active_conversation
async def show_large_order_warning(update: Update, quantity: int, support_url: str) -> Message:
    text = (
        f"⚠️ <b>Заказ в размере {quantity} звёзд нужно согласовать!</b>\n\n"
        f"Большие заказы мы не обрабатываем автоматически.\n"
        "Напиши в поддержку, чтобы оформить пополнение"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_large_order_kb(update.effective_user.id, support_url),
        photo_name=None
    )


@autosave_active_conversation
async def show_choose_recipient(update: Update) -> Message:
    text = "✨ <b>Кому отправить звёзды?</b>\n\nВыбери вариант ниже"
    return await render_screen(
        update, text,
        reply_markup=await build_recipient_kb(update.effective_user.id),
        photo_name="choose_recipient.jpg"
    )


@autosave_active_conversation
async def show_enter_username(update: Update) -> Message:
    text = "🎁 <b>Введи @username получателя</b>\n\nНапример: @pmlame"
    return await render_screen(
        update, text,
        reply_markup=await build_back_to_recipient_kb(update.effective_user.id),
        photo_name=None
    )


@autosave_active_conversation
async def show_searching_username(update: Update, username: str) -> Message:
    text = (
        f"🔎 <b>Ищем пользователя @{username.lstrip("@")}...</b>\n\nЭто займёт некоторое время\n\n"
        f"Кнопка \"Назад\" во время поиска неактивна"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_back_to_recipient_kb(update.effective_user.id),
        photo_name=None
    )


@autosave_active_conversation
async def show_user_not_found(update: Update, user: str) -> Message:
    text = f"❌ <b>Пользователь {user} не найден</b>\n\nПроверь @username и вводи снова"
    return await render_screen(
        update, text,
        reply_markup=await build_back_to_recipient_kb(update.effective_user.id),
        photo_name=None
    )


@autosave_active_conversation
async def show_payment_methods(
        update: Update,
        stars_count: int,
        active_promo: PromoCode | None,
        username: str = ""
) -> Message:
    active_promo_text = ""
    if active_promo is not None:
        active_promo_text = (
            f"Применён промокод <b>{active_promo.name}</b> на скидку <b>{active_promo.discount}%</b>\n"
            f"Промокод отменится сам в течение суток, если не будет использован"
        )

    if username:
        text = (
            f"💳 <b>Выбери способ оплаты</b>\n\nПополним звёзды для @{username.lstrip("@")}"
            f"{f'\n\n{active_promo_text}' if active_promo_text else ''}"
        )
        back_dest = BackDestination.ENTER_GIFT_USERNAME

    else:
        text = f"💸 <b>Теперь выбери способ оплаты</b>{'\n\n' + active_promo_text if active_promo_text else ''}"
        back_dest = BackDestination.CHOOSE_RECIPIENT

    payment_methods_with_prices = (
        await get_payment_methods_with_prices(active_promo, stars_count)
    )

    return await render_screen(
        update, text,
        reply_markup=await build_payment_methods_kb(
            update.effective_user.id,
            payment_methods_with_prices, back_dest
        ),
        photo_name="payment_method.jpg"
    )


def get_promo_and_price_sentences(price: Decimal, promo_name: str, promo_discount: Decimal | None) -> tuple[str, str]:
    promo_sentence = ""
    promo_remark = ""

    if promo_name and promo_discount is not None:
        promo_sentence = (
            f"🎟️ Активен промокод <b>{promo_name}</b> на скидку <b>{promo_discount:.2f}%</b>\n"
        )
        promo_remark = " (со скидкой)"

    price_sentence = f"Стоимость — {price:.2f} ₽{promo_remark}\n"

    return promo_sentence, price_sentence


@autosave_active_conversation
async def show_order_confirmation(
        update: Update,
        stars: int, price: Decimal,
        target_username: str = "",
        active_promo: PromoCode | None = None
) -> Message:
    promo_name = ""
    promo_discount = None
    if active_promo is not None:
        promo_name = active_promo.name
        promo_discount = active_promo.discount

    promo_sentence, price_sentence = get_promo_and_price_sentences(
        price, promo_name, promo_discount
    )
    if target_username:
        target_username = f"@{target_username.lstrip("@")}"
    text = (
        f"☝️ <b>Проверь заказ перед оплатой!</b>\n\n"
        f"{promo_sentence}"
        f"Пополним — ⭐ {stars} звёзд\n"
        f"{price_sentence}"
        f"{'Для кого 🎁 — ' + target_username + '\n' if target_username else ''}"
    )

    return await render_screen(
        update, text,
        reply_markup=await build_order_confirmation_kb(
            update.effective_user.id,
            BackDestination.CHOOSE_PAYMENT
        ),
        photo_name="order_confirmation.jpg"
    )


@autosave_active_conversation
async def show_pay_url_not_provided(
        update: Update,
        support_url: str
) -> Message:
    text = (
        f"🤔 <b>Платёжная система не вернула ссылку на оплату...</b>\n\n"
        f"Обратись в тех. поддержку или попробуй сделать новый заказ"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_back_to_main_menu_kb(update.effective_user.id, support_url),
        photo_name=None
    )


def get_order_created_text(
        transaction_id: UUID | str,
        stars: int, price: Decimal,
        target_username: str, expires_in: str | None = None,
        promo_name: str = "", promo_discount: Decimal | None = None
) -> str:
    promo_sentence, price_sentence = get_promo_and_price_sentences(price, promo_name, promo_discount)
    ending = get_ending_for_digit_string(expires_in, WordCase.GENITIVE)
    if target_username and target_username != TARGET_SELF:
        target_username = f"@{target_username.lstrip("@")}"
    return (
        f"📦 <b>Заказ ждёт оплату!</b>\n\n"
        f"{promo_sentence}"
        f"Пополним — ⭐ {stars} звёзд\n"
        f"{price_sentence}"
        f"{f'Для кого 🎁 — {target_username}\n' if target_username else ''}"
        f"🆔 ID заказа: <code>{transaction_id}</code>\n\n"
        f"{f'Ссылка на оплату действует {expires_in} минут{ending}\n' if expires_in else ''}"
        f"Новый заказ можно создать с помощью /start"
    )


async def edit_order_created_message(
        msg: Message,
        stars: int, price: Decimal,
        pay_url: str, transaction_id: UUID, expires_in: str | None,
        target_username: str = "",
        active_promo: PromoCode | None = None
) -> Message | None:
    promo_name = ""
    promo_discount = None
    if active_promo is not None:
        promo_name = active_promo.name
        promo_discount = active_promo.discount

    if target_username:
        target_username = f"@{target_username.lstrip("@")}"

    text = get_order_created_text(
        transaction_id, stars, price, target_username, expires_in,
        promo_name, promo_discount
    )

    return await update_existing_message(
        msg,
        text,
        reply_markup=build_order_confirmed_kb(pay_url),
        photo_name="order_confirmed.jpg"
    )


async def edit_order_creating_message(msg: Message) -> Message | None:
    text = f"⏳ <b>Заказ создаётся...</b>"
    return await update_existing_message(
        msg, text,
        reply_markup=None,
        photo_name="order_confirmation.jpg"
    )


async def edit_order_creating_failed_message(msg: Message) -> Message | None:
    text = f"❌ <b>Не удалось создать заказ</b>\n\nПопробуй ещё раз!"
    return await update_existing_message(
        msg,
        text,
        reply_markup=await build_order_confirmation_kb(
            msg.chat_id,
            BackDestination.CHOOSE_PAYMENT
        ),
        photo_name="order_confirmation.jpg"
    )
