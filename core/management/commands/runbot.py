import os
import warnings
from pathlib import Path
from typing import final, override

from django.conf import settings
from django.core.management.base import BaseCommand

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
from bot.router import get_conversation_handler, get_debug_handlers

from core.ioc import get_container, close_container


type DefaultApplication = Application[
    ExtBot[None], ContextTypes.DEFAULT_TYPE,
    dict[object,object], dict[object,object], dict[object,object],
    JobQueue[ContextTypes.DEFAULT_TYPE]
]


@final
class Command(BaseCommand):
    help = "Запуск Telegram бота"
    # Настройка кастомных тайм-аутов (в секундах)
    request_config = HTTPXRequest(
        connection_pool_size=20,  # Кол-во открытых соединений
        connect_timeout=20.0,     # Время на установку соединения
        read_timeout=25.0,        # Время ожидания ответа от серверов Telegram
        write_timeout=25.0,       # Время на отправку данных (обычный текст)
        media_write_timeout=60.0  # Время на загрузку тяжелых файлов/медиа
    )

    async def post_init(
            self,
            application: DefaultApplication
    ) -> None:
        commands = [BotCommand("start", "Сделать новый заказ")]
        if settings.DEBUG:
            user_warning = "Режим отладки - если ты обычный пользователь, сообщи об ошибке в тех. поддержку"
            commands.append(BotCommand("balance", user_warning))
            commands.append(BotCommand("balance_debug", user_warning))
            commands.append(BotCommand("prices", user_warning))
            commands.append(BotCommand("prices_debug", user_warning))
        _ = await application.bot.set_my_commands(commands)

    async def post_stop(self, application: DefaultApplication) -> None:
        self.stdout.write("Bot is stopping, closing dishka container...")

        try:
            await close_container()
            self.stdout.write("Dishka container closed successfully!")

        except Exception as err:
            self.stderr.write(f"Error while closing dishka container in bot: {err}")

    @override
    def handle(self, *args: object, **options: object):
        # Есть предупреждение о per_message=False, но оно возникает в любом случае, т. е. и при True;
        # от него зависит поведение того, как выбирается состояние для ConversationHandler;
        # при False оно одно для всех сообщений; при True то сообщение, которое генерирует функция начала Conversation,
        # будет сохранено по его id, и конкретно для него будет изменяться состояние, т.е. можно будет иметь несколько
        # Conversation со своими состояниями; в нашем случае нельзя использовать per_message=True, т.к. иногда
        # начальное сообщение от Conversation необходимо удалить и сделать новое - в таком случае id не обновится
        # для хэндлера)
        warnings.filterwarnings("ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

        self.stdout.write("Бот запускается...")

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            self.stderr.write("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
            return

        container = get_container()

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

        # .persistence(persistence) TODO: продумать персистентность
        application = (
            ApplicationBuilder()
            .token(token)
            .request(self.request_config)
            .arbitrary_callback_data(True)
            .post_init(self.post_init)
            .post_stop(self.post_stop)
            .build()
        )
        application.bot_data["dishka_container"] = container

        application.add_error_handler(error_handler)

        application.add_handler(TypeHandler(Update, register_user_middleware), group=-1)
        application.add_handler(get_conversation_handler())

        if settings.DEBUG:
            handlers = get_debug_handlers()
            for handler in handlers:
                application.add_handler(handler)

        self.stdout.write("Бот настроен! Пытаемся подключиться к серверу Telegram...")
        application.run_polling()
