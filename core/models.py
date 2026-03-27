from django.db import models
from solo.models import SingletonModel


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, verbose_name="Username")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    def __str__(self):
        return f"{self.username or self.telegram_id}"

    class Meta:
        verbose_name = "Пользователь бота"
        verbose_name_plural = "Пользователи бота"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'ОЖИДАЕТ'),
        ('SUCCESS', 'УСПЕШНО'),
        ('FAILED', 'ОШИБКА'),
    ]

    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Пользователь"
    )
    amount_fiat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    amount_stars = models.IntegerField(verbose_name="Количество звезд")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    def __str__(self):
        return f"Транзакция #{self.id} ({self.telegram_user})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"


class TransactionMetadata(models.Model):
    TYPES_CHOICES =[
        ('PURCHASE', 'Покупка'),
    ]

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='metadata_info',
        verbose_name="Транзакция"
    )
    type = models.CharField(max_length=50, choices=TYPES_CHOICES, verbose_name="Тип")
    payment_method = models.CharField(max_length=50, verbose_name="Способ оплаты")
    payload = models.JSONField(default=dict, blank=True, verbose_name="Доп. данные (JSON)")

    class Meta:
        verbose_name = "Метаданные транзакции"
        verbose_name_plural = "Метаданные транзакций"


class MonthlyProfit(Transaction):
    class Meta:
        proxy = True
        verbose_name = 'Прибыль по месяцам'
        verbose_name_plural = 'Прибыль по месяцам'


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название системы")
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        verbose_name="Комиссия (%)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    def __str__(self):
        return f"{self.name} ({self.commission_percent}%)"

    class Meta:
        verbose_name = "Метод оплаты"
        verbose_name_plural = "Методы оплаты"


class GlobalSettings(SingletonModel):
    star_base_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.35,
        verbose_name="Базовая цена одной звезды"
    )
    usd_base_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=80.0,
        verbose_name="Базовый курс USD"
    )
    is_use_usd_rate = models.BooleanField(
        default=False,
        verbose_name="Учитывать курс доллара?"
    )
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Технический перерыв"
    )

    def __str__(self):
        return "Глобальные настройки"

    class Meta:
        verbose_name = "Глобальные настройки"


class ExchangeRate(SingletonModel):
    usd_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=90.0,
        verbose_name="Текущий курс USD"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    def __str__(self):
        return f"Курс доллара: {self.usd_rate}"

    class Meta:
        verbose_name = "Курс валют"


class BotState(models.Model):
    user_id = models.BigIntegerField(unique=True)
    data = models.JSONField(default=dict)
    state = models.TextField(null=True)
