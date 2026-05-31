from collections.abc import Iterable
from decimal import Decimal
from typing import TypedDict, Unpack, override, TYPE_CHECKING

from django.db import models
from solo.models import SingletonModel

from core.domain.enums import TransactionStatus, TransactionType


class SaveKwargs(TypedDict, total=False):
    force_insert: bool
    force_update: bool
    using: str | None
    update_fields: Iterable[str] | None


class TelegramUser(models.Model):
    objects = models.Manager()
    if TYPE_CHECKING:
        transactions: models.manager.RelatedManager["Transaction"]

    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, blank=True, verbose_name="Username")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")

    @override
    def save(self, **kwargs: Unpack[SaveKwargs]):
        self.username = self.username.lstrip("@")
        super().save(**kwargs)

    @override
    async def asave(self, **kwargs: Unpack[SaveKwargs]):
        self.username = self.username.lstrip("@")
        await super().asave(**kwargs)

    @override
    def __str__(self):
        return f"{self.username or self.telegram_id}"

    class Meta:
        verbose_name = "Пользователь бота"
        verbose_name_plural = "Пользователи бота"


class Transaction(models.Model):
    objects = models.Manager()
    if TYPE_CHECKING:
        metadata_info: "TransactionMetadata"

    id = models.UUIDField(primary_key=True, verbose_name="ID платежа", help_text="Это ID из внешнего API")
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Покупатель"
    )
    amount_fiat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    amount_stars = models.IntegerField(verbose_name="Количество звезд")
    target_username = models.CharField(max_length=255, blank=True, default="Себе", verbose_name="Кому")
    status = models.CharField(max_length=20, choices=TransactionStatus.to_choices(), default=TransactionStatus.PENDING, verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Истекает")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @override
    def __str__(self):
        return f"Транзакция #{self.id} ({self.telegram_user})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"

        constraints = [
            models.UniqueConstraint(
                fields=["id", "telegram_user"],
                name="unique_user_transaction_id"
            )
        ]


class TransactionMetadata(models.Model):
    objects = models.Manager()

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="metadata_info",
        verbose_name="Транзакция"
    )
    type = models.CharField(max_length=50, choices=TransactionType.to_choices(), verbose_name="Тип")
    payment_method = models.CharField(max_length=50, verbose_name="Способ оплаты")
    payload: dict[str, object] = models.JSONField(default=dict, blank=True, verbose_name="Доп. данные (JSON)")

    @override
    def __str__(self):
        return f"Метаданные для {self.transaction}"

    class Meta:
        verbose_name = "Метаданные транзакции"
        verbose_name_plural = "Метаданные транзакций"


class MonthlyProfit(Transaction):
    class Meta:
        proxy = True
        verbose_name = "Прибыль по месяцам"
        verbose_name_plural = "Прибыль по месяцам"


class PaymentAPI(models.Model):
    objects = models.Manager()
    if TYPE_CHECKING:
        methods: models.manager.RelatedManager["PaymentMethod"]

    name = models.CharField(primary_key=True, max_length=50, verbose_name="Название API платёжных систем")

    @override
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "API платёжных систем"
        verbose_name_plural = "API платёжных систем"


class PaymentMethod(models.Model):
    objects = models.Manager()

    api = models.ForeignKey(
        PaymentAPI,
        on_delete=models.CASCADE,
        related_name="methods",
        verbose_name="API платёжных систем"
    )
    name = models.CharField(max_length=50, verbose_name="Название метода оплаты", help_text="Отображается в боте")
    external_id = models.CharField(max_length=255, verbose_name="ID метода оплаты", help_text="ID из внешнего API; Может быть числом или строкой")
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Комиссия (%)"
    )
    is_active = models.BooleanField(default=False, verbose_name="Активна")

    @override
    def __str__(self):
        return f"{self.api.name} - {self.name} ({self.commission_percent}%)"

    class Meta:
        verbose_name = "Метод оплаты"
        verbose_name_plural = "Методы оплаты"

        constraints = [
            models.UniqueConstraint(
                fields=["api", "name"],
                name="unique_api_method_name"
            )
        ]


class GlobalSettings(SingletonModel):
    objects = models.Manager()

    star_base_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.35"),
        verbose_name="Базовая цена одной звезды"
    )
    usd_base_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("80.00"),
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

    @classmethod
    async def aget_solo(cls):
        obj, is_created = await cls.objects.aget_or_create(pk=cls.singleton_instance_id)
        return obj

    def __str__(self):
        return "Глобальные настройки"

    class Meta:
        verbose_name = "Глобальные настройки"


class ExchangeRate(SingletonModel):
    objects = models.Manager()

    usd_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("90.00"),
        verbose_name="Текущий курс USD"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @classmethod
    async def aget_solo(cls):
        obj, is_created = await cls.objects.aget_or_create(pk=cls.singleton_instance_id)
        return obj

    @override
    def __str__(self):
        return f"Курс доллара: {self.usd_rate}"

    class Meta:
        verbose_name = "Курс валют"


# TODO: Вроде бы не надо, так как для Persistence будет PicklePersistence
class BotState(models.Model):
    objects = models.Manager()

    user_id = models.BigIntegerField(unique=True)
    data = models.JSONField(default=dict)
    state = models.TextField(null=True)
