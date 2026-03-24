from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils.injector import inject
from core.services.payment_service import PaymentService


RECIPIENT, USERNAME, AMOUNT, CUSTOM_AMOUNT, METHOD = range(5)


@inject
async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🙋‍♂️ Себе", callback_data="self")],
        [InlineKeyboardButton("🎁 В подарок", callback_data="gift")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]
    ])
    await query.edit_message_caption(caption="✨ Кому отправить звёзды?", reply_markup=keyboard)
    return RECIPIENT


async def recipient_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "self":
        context.user_data['target_username'] = None
        return await show_amount_selection(update, context)

    await query.edit_message_caption(caption="🎁 Введите @username получателя:")
    return USERNAME


async def gift_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.replace("@", "")
    context.user_data['target_username'] = username
    return await show_amount_selection(update, context)


async def show_amount_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "💎 Сколько покупаем звёзд?"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ 50", callback_data="50"), InlineKeyboardButton("⭐ 100", callback_data="100")],
        [InlineKeyboardButton("⭐ 250", callback_data="250"), InlineKeyboardButton("⭐ 500", callback_data="500")],
        [InlineKeyboardButton("✏️ Своё количество", callback_data="custom")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_recipient")]
    ])

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_caption(caption=text, reply_markup=keyboard)
    return AMOUNT


async def amount_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "custom":
        await query.edit_message_caption(caption="Введите количество звёзд (минимум 50):")
        return CUSTOM_AMOUNT

    context.user_data['stars_count'] = int(query.data)
    return await show_method_selection(update, context)


async def custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text)
        if val < 50: raise ValueError
        context.user_data['stars_count'] = val
        return await show_method_selection(update, context)
    except:
        await update.message.reply_text("Пожалуйста, введите число больше 50:")
        return CUSTOM_AMOUNT


@inject
async def show_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_service: PaymentService):
    stars = context.user_data['stars_count']

    price_sbp = await payment_service._star_service.get_order_price(stars, "sbp")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔹 СБП — {price_sbp}₽", callback_data="sbp")],
        [InlineKeyboardButton(f"💳 Карта — {price_sbp}₽", callback_data="card")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_amount")]
    ])

    text = f"🛒 Заказ: {stars} ⭐\nВыберите способ оплаты:"
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.callback_query.edit_message_caption(caption=text, reply_markup=keyboard)
    return METHOD


@inject
async def handle_payment_choice(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        payment_service: PaymentService
):
    query = update.callback_query
    method = query.data  # 'sbp', 'card' or 'ton'

    stars_count = context.user_data['stars_count']
    target = context.user_data.get('target_username')

    try:
        payment_dto = await payment_service.create_checkout(
            user_id=query.from_user.id,
            stars_count=stars_count,
            method=method,
            target_username=target
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("💳 Оплатить", url=payment_dto.pay_url)
        ]])

        await query.edit_message_caption(
            caption=f"Ваш заказ: {stars_count} ⭐\nК оплате: {payment_dto.amount} ₽",
            reply_markup=keyboard
        )
    except Exception as e:
        await query.answer(str(e), show_alert=True)