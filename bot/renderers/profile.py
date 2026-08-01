from telegram import Update, Message

from bot.keyboards.profile import build_profile_kb, build_order_history_kb
from bot.renderers.base import render_screen
from bot.utils.active_conversation import autosave_active_conversation

from core.dto.stats import OrderHistoryPageDTO
from core.dto.user import UserProfileDTO


@autosave_active_conversation
async def show_profile_page(update: Update, profile_data: UserProfileDTO) -> Message:
    if not isinstance(profile_data, UserProfileDTO):
        profile_data = UserProfileDTO(-1, -1, -1)

    text = (
        "👻 <b>Мой профиль</b>\n\n"
        f"🙊 Telegram ID: <code>{profile_data.telegram_id}</code>\n"
        f"🛍 Покупок: {profile_data.purchases_count}\n"
        f"⭐ Звёзд куплено: {profile_data.stars_bought}\n"
    )
    return await render_screen(
        update, text,
        reply_markup=await build_profile_kb(update.effective_user.id),
        photo_name="profile.jpg"
    )


@autosave_active_conversation
async def show_order_history_page(update: Update, history_dto: OrderHistoryPageDTO) -> Message:
    if not history_dto.items:
        orders_text = "<i>У вас пока нет заказов</i>"
    else:
        lines = [
            f"{item.date} — ⭐ {item.stars} звёзд — {item.price} ₽"
            for item in history_dto.items
        ]
        orders_text = "\n".join(lines)

    text = (
        "📦 <b>История покупок</b>\n\n"
        "Дата покупки — Кол-во звёзд — Цена\n"
        f"{orders_text}"
    )

    return await render_screen(
        update, text,
        reply_markup=await build_order_history_kb(
            update.effective_user.id,
            history_dto.current_page, history_dto.total_pages
        ),
        photo_name="history.jpg"
    )
