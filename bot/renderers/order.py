from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.order import *


async def show_choose_quantity(update: Update):
    text = "🧠 Сколько покупаем звёзд?\n\nПоказываем самые популярные варианты.\nМожно ввести своё количество ;)"
    await render_screen(update, text, build_quantity_kb(), "choose_quantity.jpg")


async def show_custom_quantity_input(update: Update):
    text = "🌟 Введи количество звёзд\n\nМинимум 50."
    await render_screen(update, text, build_back_to_quantity_kb())


async def show_large_order_warning(update: Update, support_url: str):
    text = "⚠️ Такой заказ нужно согласовать!\n\nБольшие заказы мы не обрабатываем автоматически.\nНапиши в поддержку, чтобы оформить пополнение."
    await render_screen(update, text, build_large_order_kb(support_url))


async def show_choose_recipient(update: Update):
    text = "✨ Кому отправить звёзды?\n\nВыбери вариант ниже."
    await render_screen(update, text, build_recipient_kb(), "choose_recipient.jpg")


async def show_enter_username(update: Update):
    text = "🎁 Введи @username получателя\n\nНапример: @dween"
    await render_screen(update, text, build_back_to_recipient_kb())


async def show_user_not_found(update: Update):
    text = "❌ Пользователь не найден\n\nПроверь @username и повтори попытку."
    await render_screen(update, text, build_user_not_found_kb())


async def show_payment_methods(update: Update, sbp_price: float, card_price: float, is_gift: bool,
                               username: str = None):
    if is_gift:
        text = f"💳 Выбери способ оплаты\n\nПополним звёзды для {username}.\nВыбери: СБП или Картой."
        back_dest = BackDestination.ENTER_GIFT_USERNAME
        photo = "payment_method_gift.jpg"
    else:
        text = "💸 Теперь выбери способ оплаты\n\nВыбери: СБП или Картой."
        back_dest = BackDestination.CHOOSE_RECIPIENT
        photo = "payment_method_self.jpg"

    await render_screen(update, text, build_payment_methods_kb(sbp_price, card_price, back_dest), photo)


async def show_order_confirmation(update: Update, stars: int, price: float, pay_url: str, is_gift: bool):
    text = f"☝️ Проверь заказ перед оплатой!\n\nПополним — ⭐ {stars} звёзд\nСтоимость — {price} ₽\n\nСсылка на оплату действует 30 минут."
    back_dest = BackDestination.CHOOSE_PAYMENT_GIFT if is_gift else BackDestination.CHOOSE_PAYMENT_SELF
    photo = "order_confirmation_gift.jpg" if is_gift else "order_confirmation_self.jpg"

    await render_screen(update, text, build_confirmation_kb(pay_url, back_dest, not is_gift), photo)
