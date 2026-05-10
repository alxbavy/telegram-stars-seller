from decimal import Decimal

from telegram import Update, Message
from bot.renderers.base import render_screen
from bot.keyboards.order import *


async def show_choose_quantity(update: Update):
    text = "🧠 <b>Сколько покупаем звёзд?</b>\n\nПоказываем самые популярные варианты.\nМожно ввести своё количество ;)"
    return await render_screen(update, text, build_quantity_kb(), "choose_quantity.jpg")


async def show_custom_quantity_input(update: Update):
    text = "🌟 <b>Введи количество звёзд</b>\n\nМинимум 50."
    return await render_screen(update, text, build_back_to_quantity_kb())


async def show_large_order_warning(update: Update, support_url: str):
    text = "⚠️ <b>Такой заказ нужно согласовать!</b>\n\nБольшие заказы мы не обрабатываем автоматически.\nНапиши в поддержку, чтобы оформить пополнение."
    return await render_screen(update, text, build_large_order_kb(support_url))


async def show_choose_recipient(update: Update):
    text = "✨ <b>Кому отправить звёзды?</b>\n\nВыбери вариант ниже."
    return await render_screen(update, text, build_recipient_kb(), "choose_recipient.jpg")


async def show_enter_username(update: Update):
    text = "🎁 <b>Введи @username получателя</b>\n\nНапример: @dween"
    return await render_screen(update, text, build_back_to_recipient_kb())


async def show_user_not_found(update: Update, user: str):
    text = f"❌ <b>Пользователь {user} не найден</b>\n\nПроверь @username и повтори попытку."
    return await render_screen(update, text, build_user_not_found_kb())


async def show_payment_methods(
        update: Update,
        sbp_price: Decimal,
        card_price: Decimal,
        is_gift: bool,
        username: str = None
):
    if is_gift:
        text = f"💳 <b>Выбери способ оплаты</b>\n\nПополним звёзды для {username}.\nВыбери: СБП или Картой."
        back_dest = BackDestination.ENTER_GIFT_USERNAME
        photo = "payment_method_gift.jpg"
    else:
        text = "💸 <b>Теперь выбери способ оплаты</b>\n\nВыбери: СБП или Картой."
        back_dest = BackDestination.CHOOSE_RECIPIENT
        photo = "payment_method_self.jpg"

    return await render_screen(update, text, build_payment_methods_kb(sbp_price, card_price, back_dest), photo)


async def show_order_confirmation(
        update: Update,
        stars: int,
        price: Decimal,
        pay_url: str,
        is_gift: bool,
        target_username: str = ""
):
    text = (
        f"☝️ <b>Проверь заказ перед оплатой!</b>\n\nПополним — ⭐ {stars} звёзд\nСтоимость — {price} ₽\n"
        f"{'Для кого 🎁 — ' + target_username + '\n' if target_username else '\n'}"
        f"Ссылка на оплату действует 30 минут."
    )
    back_dest = BackDestination.CHOOSE_PAYMENT_GIFT if is_gift else BackDestination.CHOOSE_PAYMENT_SELF
    photo = "order_confirmation_gift.jpg" if is_gift else "order_confirmation_self.jpg"

    return await render_screen(update, text, build_confirmation_kb(pay_url, back_dest, not is_gift), photo)
