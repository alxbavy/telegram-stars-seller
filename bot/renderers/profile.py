from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.profile import build_profile_kb, build_order_history_kb
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


async def show_order_history_page(update: Update, page: int = 1):
    total_pages = 2

    if page == 1:
        orders_text = (
            "12.03.2026 — ⭐ 50 звёзд — 60 ₽\n"
            "22.03.2026 — ⭐ 150 звёзд — 180 ₽\n"
            "03.03.2026 — ⭐ 250 звёзд — 300 ₽"
        )
    else:
        orders_text = (
            "01.03.2026 — ⭐ 1000 звёзд — 1200 ₽\n"
            "28.02.2026 — ⭐ 50 звёзд — 60 ₽"
        )

    text = (
        "📦 <b>История заказов</b>\n\n"
        "Дата покупки — Кол-во звёзд — Цена\n"
        f"{orders_text}"
    )

    await render_screen(update, text, build_order_history_kb(page, total_pages), "history.jpg")