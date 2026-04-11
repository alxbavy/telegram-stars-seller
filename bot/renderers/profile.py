from telegram import Update
from bot.renderers.base import render_screen
from bot.keyboards.profile import build_profile_kb, build_order_history_kb


async def show_profile_page(update: Update):
    user_id = update.effective_user.id

    text = (
        "👻 <b>Мой профиль</b>\n\n"
        f"🙊 Telegram ID: <code>{user_id}</code>\n"
        "🛍 Покупок: 0\n"
        "⭐ Звёзд куплено: 0\n"
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