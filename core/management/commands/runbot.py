import os

from django.core.management.base import BaseCommand
from dishka import make_async_container
from telegram import Update
from telegram.ext import ApplicationBuilder, TypeHandler

from bot.middlewares.user import register_user_middleware
from core.ioc import BusinessLogicProvider
from bot.router import get_conversation_handler

class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        self.stdout.write("Бот запускается...")

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.stderr.write("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
            return

        container = make_async_container(BusinessLogicProvider())

        application = (
            ApplicationBuilder()
            .token(token)
            .arbitrary_callback_data(True)
            .build()
        )
        application.bot_data["dishka_container"] = container

        application.add_handler(TypeHandler(Update, register_user_middleware), group=-1)
        application.add_handler(get_conversation_handler())

        application.run_polling()
