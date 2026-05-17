import json

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, JsonResponse, HttpResponse
from telegram.ext import ExtBot

from bot.keyboards.order import build_repeat_order_kb

from core.integrations.fragment import FragmentAPIError
from core.services.payment import PaymentService
from core.business_logic_container import container


@csrf_exempt
async def payment_webhook(request: HttpRequest):
    """
    Заглушка для обработки вебхука от платежной системы.
    Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot.
    """
    print("webhook called")
    return HttpResponse(status=200)  # TODO: заглушка

    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    data = json.loads(request.body)
    transaction_id = data.get("transaction_id")  # TODO: валидация

    # TODO: закончить вебхук
    async with container() as request_container:
        payment_service = await request_container.get(PaymentService)  # TODO: надо перейти на Postgres
        _ = await payment_service.confirm_payment(transaction_id)

    # 2. Отправка уведомления пользователю вне ConversationHandler
    bot: ExtBot[None] = ExtBot(token=settings.TELEGRAM_BOT_TOKEN)

    # Пример отправки (Состояние 12)
    text = "😊 Заказ успешно доставлен!\n\nПополнили — ⭐ 50 звёзд\n\nСпасибо за покупку! ❤️"
    await bot.send_photo(
        chat_id=123456789,  # transaction.telegram_user.telegram_id
        photo="https://dummyimage.com/600x400/000/fff&text=order_success_self.jpg",
        caption=text,
        reply_markup=build_repeat_order_kb()
    )

    return JsonResponse({"status": "ok"})
