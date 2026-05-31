import os
from pathlib import Path
from typing import Any, cast, final, override
import warnings

from django.conf import settings
from django.core.management.base import BaseCommand
from dishka import AsyncContainer, make_async_container
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder, Application, ExtBot,
    JobQueue,
    ContextTypes,
    TypeHandler,
    PicklePersistence, PersistenceInput
)
from telegram.request import HTTPXRequest
from telegram.warnings import PTBUserWarning

from bot.handlers.error import error_handler
from bot.middlewares.user import register_user_middleware
from bot.router import get_conversation_handler

from core.services.payment import PaymentService
from core.ioc import BusinessLogicProvider


type DefaultApplication = Application[
    ExtBot[None], ContextTypes.DEFAULT_TYPE,
    dict[Any,Any], dict[Any,Any], dict[Any,Any],
    JobQueue[ContextTypes.DEFAULT_TYPE]
]


@final
class Command(BaseCommand):
    help = "Запуск Telegram бота"
    # Настройка кастомных таймаутов (в секундах)
    request_config = HTTPXRequest(
        connect_timeout=20.0,     # Время на установку соединения
        read_timeout=25.0,        # Время ожидания ответа от серверов Telegram
        write_timeout=25.0,       # Время на отправку данных (обычный текст)
        media_write_timeout=60.0  # Время на загрузку тяжелых файлов/медиа
    )

    async def post_init(
            self,
            application: DefaultApplication
    ) -> None:
        _ = await application.bot.set_my_commands([
            BotCommand("start", "Сделать новый заказ"),
        ])

        container = cast(AsyncContainer, application.bot_data["dishka_container"])
        async with container() as request_container:
            payment_service = await request_container.get(PaymentService)

            self.stdout.write("Очищаем протухшие транзакции (возрастом более 1 часа)...")
            await payment_service.delete_transactions("01:00:00")
            self.stdout.write("Очистка протухших транзакций (возрастом более 1 часа) завершена!")

    @override
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

        # data_dir = Path(settings.BASE_DIR) / "bot" / "data"
        # data_dir.mkdir(parents=True, exist_ok=True)
        # filepath = data_dir / "bot_persistence.pickle"
        #
        # persistence = PicklePersistence(
        #     filepath=filepath,
        #     store_data=PersistenceInput(
        #         bot_data=False
        #     ),
        #     update_interval=30
        # )

        # .persistence(persistence) TODO: раскомментировать в релизе, в дебаге персистентность мешает
        application = (
            ApplicationBuilder()
            .token(token)
            .request(self.request_config)
            .arbitrary_callback_data(True)
            .post_init(self.post_init)
            .build()
        )
        application.bot_data["dishka_container"] = container

        application.add_error_handler(error_handler)

        application.add_handler(TypeHandler(Update, register_user_middleware), group=-1)
        application.add_handler(get_conversation_handler())

        self.stdout.write("Бот настроен! Пытаемся подключиться к серверу Telegram...")
        application.run_polling()
