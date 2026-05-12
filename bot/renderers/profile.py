from telegram import Update, Message

from bot.renderers.base import render_screen
from bot.keyboards.profile import build_profile_kb, build_order_history_kb
from core.dto.stats import OrderHistoryPageDTO
from core.dto.user import UserProfileDTO


async def show_profile_page(update: Update, profile_data: UserProfileDTO):
    if not isinstance(profile_data, UserProfileDTO):
        profile_data = UserProfileDTO(-1, -1, -1)

    text = (
        "👻 <b>Мой профиль</b>\n\n"
        f"🙊 Telegram ID: <code>{profile_data.telegram_id}</code>\n"
        f"🛍 Покупок: {profile_data.purchases_count}\n"
        f"⭐ Звёзд куплено: {profile_data.stars_bought}\n"
    )
    return await render_screen(update, text, build_profile_kb(), "profile.jpg")


async def show_order_history_page(update: Update, history_dto: OrderHistoryPageDTO):
    if not history_dto.items:
        orders_text = "<i>У вас пока нет заказов</i>"
    else:
        lines = [
            f"{item.date} — ⭐ {item.stars} звёзд — {item.price} ₽"
            for item in history_dto.items
        ]
        orders_text = "\n".join(lines)

    text = (
        "📦 <b>История заказов</b>\n\n"
        "Дата покупки — Кол-во звёзд — Цена\n"
        f"{orders_text}"
    )

    return await render_screen(
        update,
        text,
        build_order_history_kb(history_dto.current_page, history_dto.total_pages),
        "history.jpg"
    )
