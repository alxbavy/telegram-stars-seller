from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.profile import build_profile_kb, build_order_history_kb
from core.dto.stats import OrderHistoryPageDTO
from core.dto.user import UserProfileDTO


async def show_profile_page(update: Update, profile_data: UserProfileDTO):
    telegram_id = getattr(profile_data, "telegram_id", None)
    orders_count = getattr(profile_data, "orders_count", 0)
    total_stars = getattr(profile_data, "total_stars", 0)

    text = (
        "👻 <b>Мой профиль</b>\n\n"
        f"🙊 Telegram ID: <code>{telegram_id}</code>\n"
        f"🛍 Покупок: {orders_count}\n"
        f"⭐ Звёзд куплено: {total_stars}\n"
    )
    await render_screen(update, text, build_profile_kb(), "profile.jpg")


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

    await render_screen(
        update,
        text,
        build_order_history_kb(history_dto.current_page, history_dto.total_pages),
        "history.jpg"
    )
