import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram.ext import ExtBot
from django.conf import settings
from bot.keyboards.order import build_repeat_order_kb


@csrf_exempt
async def payment_webhook(request):
    """
    Заглушка для обработки вебхука от платежной системы.
    Вызывает сервисы для обновления статуса и отправляет сообщение через PTB Bot.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        transaction_id = data.get("transaction_id")

        # 1. Вызов PaymentService.confirm_payment(transaction_id)
        # transaction = await payment_service.confirm_payment(transaction_id)

        # 2. Отправка уведомления пользователю вне ConversationHandler
        bot: ExtBot = ExtBot(token=settings.TELEGRAM_BOT_TOKEN)

        # Пример отправки (Состояние 12)
        text = "😊 Заказ успешно доставлен!\n\nПополнили — ⭐ 50 звёзд\n\nСпасибо за покупку! ❤️"
        await bot.send_photo(
            chat_id=123456789,  # transaction.telegram_user.telegram_id
            photo="https://dummyimage.com/600x400/000/fff&text=order_success_self.jpg",
            caption=text,
            reply_markup=build_repeat_order_kb()
        )

        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "method not allowed"}, status=405)
