from decimal import Decimal
from uuid import UUID

from telegram import Update, Message

from bot.keyboards.main import build_back_to_main_menu_kb
from bot.renderers.base import render_screen, update_existing_message
from bot.keyboards.order import (
    build_quantity_kb,
    build_back_to_quantity_kb,
    build_large_order_kb,
    build_recipient_kb,
    build_back_to_recipient_kb,
    build_payment_methods_kb_static,
    build_payment_methods_kb_dynamic,
    build_order_confirmation_kb, build_order_confirmed_kb
)
from bot.utils.active_conversation import autosave_active_conversation, autosave_active_conversation_with_context
from bot.utils.injector import inject_without_context
from bot.enums import BackDestination
from bot.utils.string_helpers import WordCase, get_ending_for_digit_string
from core.models import PromoCode

from core.repositories.utils import db_action_with_tenacity
from core.services.payment import PaymentService
from core.services.promo_code import PromoCodeService
from core.services.star_price import StarService


@autosave_active_conversation
async def show_choose_quantity(update: Update) -> Message:
    text = (
        "🧠 <b>Сколько покупаем звёзд?</b>\n\nПоказываем самые популярные варианты.\n"
        "Можно ввести своё количество ;)"
    )
    return await render_screen(update, text, build_quantity_kb(), "choose_quantity.jpg")


@autosave_active_conversation
async def show_custom_quantity_input(update: Update) -> Message:
    text = "🌟 <b>Введи количество звёзд</b>\n\nМинимум 50"
    return await render_screen(update, text, build_back_to_quantity_kb())


@autosave_active_conversation
async def show_large_order_warning(update: Update, quantity: int, support_url: str) -> Message:
    text = (
        f"⚠️ <b>Заказ в размере {quantity} звёзд нужно согласовать!</b>\n\n"
        f"Большие заказы мы не обрабатываем автоматически.\n"
        "Напиши в поддержку, чтобы оформить пополнение"
    )
    return await render_screen(update, text, build_large_order_kb(support_url))


@autosave_active_conversation
async def show_choose_recipient(update: Update) -> Message:
    text = "✨ <b>Кому отправить звёзды?</b>\n\nВыбери вариант ниже"
    return await render_screen(update, text, build_recipient_kb(), "choose_recipient.jpg")


@autosave_active_conversation
async def show_enter_username(update: Update) -> Message:
    text = "🎁 <b>Введи @username получателя</b>\n\nНапример: @pmlame"
    return await render_screen(update, text, build_back_to_recipient_kb())


@autosave_active_conversation
async def show_searching_username(update: Update, username: str) -> Message:
    text = (
        f"🔎 <b>Ищем пользователя {username}...</b>\n\nЭто займёт некоторое время\n\n"
        f"Кнопка \"Назад\" во время поиска неактивна"
    )
    return await render_screen(update, text, build_back_to_recipient_kb())


@autosave_active_conversation
async def show_user_not_found(update: Update, user: str) -> Message:
    text = f"❌ <b>Пользователь {user} не найден</b>\n\nПроверь @username и повтори попытку"
    return await render_screen(update, text, build_back_to_recipient_kb())


@autosave_active_conversation
async def show_payment_methods_static(
        update: Update,
        sbp_price: Decimal, card_price: Decimal,
        is_gift: bool, username: str | None = None
) -> Message:
    if is_gift:
        text = f"💳 <b>Выбери способ оплаты</b>\n\nПополним звёзды для {username}.\nВыбери: СБП или Картой"
        back_dest = BackDestination.ENTER_GIFT_USERNAME
        photo = "payment_method_gift.jpg"
    else:
        text = "💸 <b>Теперь выбери способ оплаты</b>\n\nВыбери: СБП или Картой"
        back_dest = BackDestination.CHOOSE_RECIPIENT
        photo = "payment_method_self.jpg"

    return await render_screen(update, text, build_payment_methods_kb_static(sbp_price, card_price, back_dest), photo)


@autosave_active_conversation_with_context
@inject_without_context
async def show_payment_methods_dynamic(
        update: Update,
        stars_count: int,
        username: str = "",
        *,
        promo_service: PromoCodeService, payment_service: PaymentService, star_service: StarService
) -> Message:
    active_promo = await db_action_with_tenacity(
        promo_service.get_active_promo_for_telegram_user_id(update.effective_user.id)
    )
    active_promo_text = ""
    if active_promo is not None:
        active_promo_text = (
            f"Применён промокод <b>{active_promo.name}</b> на скидку <b>{active_promo.discount}%</b>\n"
            f"Промокод отменится сам в течение суток, если не будет использован"
        )

    is_gift = (True if username else False)

    if is_gift:
        text = (
            f"💳 <b>Выбери способ оплаты</b>\n\nПополним звёзды для {username}"
            f"{f'\n\n{active_promo_text}' if active_promo_text else ''}"
        )
        back_dest = BackDestination.ENTER_GIFT_USERNAME
        photo = "payment_method_gift.jpg"
    else:
        text = f"💸 <b>Теперь выбери способ оплаты</b>{'\n\n' + active_promo_text if active_promo_text else ''}"
        back_dest = BackDestination.CHOOSE_RECIPIENT
        photo = "payment_method_self.jpg"

    return await render_screen(
        update, text,
        await build_payment_methods_kb_dynamic(
            stars_count, payment_service, star_service, active_promo, back_dest
        ),
        photo
    )


def _get_promo_and_price_sentences(price: Decimal, promo_name: str, promo_discount: Decimal | None) -> tuple[str, str]:
    display_price = price
    promo_sentence = ""
    promo_remark = ""

    if promo_name and promo_discount is not None:
        display_price = price * (1 - promo_discount / 100)
        promo_sentence = (
            f"🎟️ Активен промокод <b>{promo_name}</b> на скидку <b>{promo_discount:.2f}%</b>\n"
        )
        promo_remark = " (со скидкой)"

    price_sentence = f"Стоимость — {display_price:.2f} ₽{promo_remark}\n"

    return promo_sentence, price_sentence


@autosave_active_conversation
async def show_order_confirmation(
        update: Update,
        stars: int, price: Decimal,
        is_gift: bool, target_username: str | None = None,
        active_promo: PromoCode | None = None
) -> Message:
    promo_name = ""
    promo_discount = None
    if active_promo is not None:
        promo_name = active_promo.name
        promo_discount = active_promo.discount

    promo_sentence, price_sentence = _get_promo_and_price_sentences(
        price, promo_name, promo_discount
    )
    text = (
        f"☝️ <b>Проверь заказ перед оплатой!</b>\n\n"
        f"{promo_sentence}"
        f"Пополним — ⭐ {stars} звёзд\n"
        f"{price_sentence}"
        f"{'Для кого 🎁 — ' + target_username + '\n' if target_username else ''}"
    )

    if is_gift:
        back_dest = BackDestination.CHOOSE_PAYMENT_GIFT
        photo = "order_confirmation_gift.jpg"
    else:
        back_dest = BackDestination.CHOOSE_PAYMENT_SELF
        photo = "order_confirmation_self.jpg"

    return await render_screen(update, text, build_order_confirmation_kb(back_dest), photo)


@autosave_active_conversation
async def show_pay_url_not_provided(
        update: Update,
        support_url: str
) -> Message:
    text = (
        f"🤔 <b>Платёжная система не вернула ссылку на оплату...</b>\n\n"
        f"Обратись в тех. поддержку или попробуй сделать новый заказ"
    )
    return await render_screen(update, text, build_back_to_main_menu_kb(support_url), photo_name=None)


def get_order_created_text(
        transaction_id: UUID | str,
        stars: int, price: Decimal,
        target_username: str | None, expires_in: str | None = None,
        promo_name: str = "", promo_discount: Decimal | None = None
) -> str:
    promo_sentence, price_sentence = _get_promo_and_price_sentences(price, promo_name, promo_discount)
    ending = get_ending_for_digit_string(expires_in, WordCase.GENITIVE)
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
        is_gift: bool, target_username: str | None = None,
        active_promo: PromoCode | None = None
) -> Message | None:
    promo_name = ""
    promo_discount = None
    if active_promo is not None:
        promo_name = active_promo.name
        promo_discount = active_promo.discount

    text = get_order_created_text(
        transaction_id, stars, price, target_username, expires_in,
        promo_name, promo_discount
    )
    photo = "order_confirmed_gift.jpg" if is_gift else "order_confirmed_self.jpg"
    return await update_existing_message(
        msg,
        text, build_order_confirmed_kb(pay_url), photo
    )


async def edit_order_creating_message(msg: Message, is_gift: bool) -> Message | None:
    text = f"⏳ <b>Заказ создаётся...</b>"
    photo = "order_confirmation_gift.jpg" if is_gift else "order_confirmation_self.jpg"
    return await update_existing_message(msg, text, reply_markup=None, photo_name=photo)


async def edit_order_creating_failed_message(msg: Message, is_gift: bool) -> Message | None:
    text = f"❌ <b>Не удалось создать заказ</b>\n\nПопробуй ещё раз!"

    if is_gift:
        back_dest = BackDestination.CHOOSE_PAYMENT_GIFT
        photo = "order_confirmation_gift.jpg"
    else:
        back_dest = BackDestination.CHOOSE_PAYMENT_SELF
        photo = "order_confirmation_self.jpg"

    return await update_existing_message(
        msg,
        text,
        build_order_confirmation_kb(back_dest),
        photo
    )
