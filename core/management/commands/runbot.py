import os
import warnings

from django.core.management.base import BaseCommand
from dishka import make_async_container
from telegram import Update
from telegram.ext import ApplicationBuilder, TypeHandler
from telegram.warnings import PTBUserWarning

from bot.middlewares.user import register_user_middleware
from core.ioc import BusinessLogicProvider
from bot.router import get_conversation_handler

class Command(BaseCommand):
    help = "Запуск Telegram бота"

    def handle(self, *args, **options):
        # TODO: раскомментировать при релизе (сейчас возникает предупреждение о per_message=False, но оно возникает в любом
        #       случае, т. е. и при True; от него зависит поведение того, как выбирается состояние для ConversationHandler;
        #       при False оно одно для всех сообщений; при True то сообщение, которое генерирует функция начала Conversation,
        #       будет сохранено по его id, и конкретно для него будет изменяться состояние, т.е. можно будет иметь несколько
        #       Conversation со своими состояниями; в нашем случае нельзя использовать per_message=True, т.к. иногда
        #       начальное сообщение от Conversation необходимо удалить и сделать новое - в таком случае id не обновится
        #       для хэндлера)
        # warnings.filterwarnings("ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

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
