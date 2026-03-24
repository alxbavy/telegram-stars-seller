import os

from django.core.management.base import BaseCommand
from dishka import make_async_container
from telegram.ext import ApplicationBuilder, ConversationHandler, CallbackQueryHandler, MessageHandler, filters

from bot.handlers.conversations.order import start_order, RECIPIENT, USERNAME, AMOUNT, CUSTOM_AMOUNT, METHOD, \
    handle_payment_choice, amount_choice, recipient_choice, gift_username, custom_amount
from core.ioc import BusinessLogicProvider

class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        self.stdout.write("Бот запускается...")

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.stderr.write("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
            return

        container = make_async_container(BusinessLogicProvider())

        application = ApplicationBuilder().token("TOKEN").persistence(persistence).build()
        application.bot_data["dishka_container"] = container

        order_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(start_order, pattern="^buy_stars$")],
            states={
                RECIPIENT: [CallbackQueryHandler(recipient_choice, pattern="^(self|gift)$")],
                USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_username)],
                AMOUNT: [CallbackQueryHandler(amount_choice, pattern="^\d+$|custom")],
                CUSTOM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_amount)],
                METHOD: [CallbackQueryHandler(handle_payment_choice, pattern="^(sbp|card|ton)$")],
            },
            fallbacks=[],
            name="order_flow",
            persistent=True
        )

        application.add_handler(order_conv)

        application.run_polling()
