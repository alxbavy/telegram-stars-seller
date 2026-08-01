from telegram import Update, Message

from bot.keyboards.promo_code import build_promo_kb
from bot.renderers.base import render_screen
from bot.utils.active_conversation import autosave_active_conversation

from core.models import PromoCode


@autosave_active_conversation
async def show_enter_promo(update: Update, active_promo: PromoCode | None) -> Message:
    text = (
        f"<b>Введи промокод:</b>\n\n"
        f"{(
            f'Применён промокод <b>{active_promo.name}</b> на скидку <b>{active_promo.discount}%</b>\n'
            f'Промокод отменится сам, если не использовать его в течение суток, либо можно отменить самому — '
            f'он не потратится\n\n'
        )
        if active_promo is not None
        else ''
        }"
        f"(Регистр букв важен; одновременно может быть активен только один промокод)"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_promo_kb(update.effective_user.id, active_promo),
        photo_name="input_promo.jpg"
    )


@autosave_active_conversation
async def show_promo_success(update: Update, promo: PromoCode, usage_left_account: int) -> Message:
    promo_applying = ""
    if promo.usage_account is None:
        promo_applying = f"{usage_left_account if usage_left_account <= 1000 else '>1000'} (глобальная деактивация)"
    elif promo.usage_account == 1:
        promo_applying = "одноразовый"
    elif promo.usage_account > 1:
        promo_applying = f"{usage_left_account if usage_left_account <= 1000 else '>1000'}"

    text = (
        f"✅ <b>Промокод {promo.name} активирован!</b>\n\n"
        f"Скидка — <b>{promo.discount:.2f}%</b>\n"
        f"Осталось применений — <b>{promo_applying}</b>\n\n"
        f"Промокод отменится сам, если не использовать его в течение суток, либо можно отменить самому — он не потратится"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_promo_kb(update.effective_user.id, promo),
        photo_name=None
    )


async def show_promo_not_found(update: Update, promo_name: str) -> Message:
    text = (
        f"❌ Промокод <b>{promo_name}</b> не найден...\n\n"
        f"Можешь попробовать снова"
    )
    return await render_screen(update, text, reply_markup=None)


async def show_promo_not_active(update: Update, promo_name: str) -> Message:
    text = (
        f"😥 <b>Промокод {promo_name} в данный момент отключен</b>\n\n"
        f"Попробуй ввести другой промокод! ❤️"
    )
    return await render_screen(update, text, reply_markup=None)


async def show_promo_exhaust_for_account(update: Update, promo_name: str, is_hold: bool) -> Message:
    text_for_promo_is_hold = ""
    if is_hold:
        text_for_promo_is_hold = (
            f"Сейчас у тебя есть неоплаченный заказ - если ты решил его не оплачивать, "
            f"то со временем он сам отменится, и тебе придёт сообщение о доступности этого промокода"
        )

    text = (
        f"👀 <b>У тебя не осталось применений для промокода {promo_name}!</b>\n\n"
        f"{text_for_promo_is_hold if text_for_promo_is_hold else 'Попробуй ввести другой промокод! ❤️'}"
    )
    return await render_screen(update, text, reply_markup=None)


async def show_promo_exhaust_for_global(update: Update, promo_name: str, is_hold: bool) -> Message:
    text_for_promo_is_hold = ""
    if is_hold:
        text_for_promo_is_hold = (
            f"Сейчас у кого-то есть неоплаченные заказы с этим промокодом - если они будут отменены, "
            f"то он снова будет доступен!\nПопробуй ввести его позже"
        )

    text = (
        f"👀 <b>Промокод {promo_name} закончился!</b>\n\n"
        f"{text_for_promo_is_hold if text_for_promo_is_hold else 'Попробуй ввести другой промокод! ❤️'}"
    )
    return await render_screen(update, text, reply_markup=None)


async def show_promo_is_processing(update: Update) -> Message:
    text = "⏳ <b>Подожди — бот проверяет промокод...</b>"
    return await render_screen(update, text, reply_markup=None)
