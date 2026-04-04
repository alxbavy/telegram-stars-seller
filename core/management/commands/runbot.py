import os

from django.core.management.base import BaseCommand
from dishka import make_async_container
from telegram.ext import ApplicationBuilder

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

        application = ApplicationBuilder().token(token).build()
        application.bot_data["dishka_container"] = container

        application.add_handlers([])

        application.run_polling()
