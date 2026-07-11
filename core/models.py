from collections.abc import Iterable
from decimal import Decimal
from typing import TypedDict, Unpack, override, TYPE_CHECKING

from django.db import models
from solo.models import SingletonModel

from core.domain.enums import TransactionStatus, TransactionType
from core.integrations.fragment.enums import FragmentStatus


TARGET_SELF = "Себе"


class SaveKwargs(TypedDict, total=False):
    force_insert: bool
    force_update: bool
    using: str | None
    update_fields: Iterable[str] | None


class PromoCode(models.Model):
    objects = models.Manager()
    if TYPE_CHECKING:
        telegram_users: models.manager.RelatedManager["TelegramUser"]
        id: int

    name = models.CharField(max_length=50, verbose_name="Промокод", help_text="Только название; регистр учитывается")
    discount = models.DecimalField(
        default=Decimal("0.00"),
        decimal_places=2,
        max_digits=5,
        verbose_name="Скидка %",
        help_text="Указывается в %, например, 5.00 (не 0.05)"
    )
    usage_account = models.BigIntegerField(null=True, blank=True, verbose_name="На аккаунт", help_text="Если пусто - без ограничений")
    usage_global = models.BigIntegerField(null=True, blank=True, verbose_name="Всего", help_text="Если пусто - без ограничений")
    is_active = models.BooleanField(default=True, verbose_name="Активен?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @override
    def __str__(self):
        return f"{self.name} {self.discount}%"

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"


class TelegramUser(models.Model):
    objects = models.Manager()
    if TYPE_CHECKING:
        transactions: models.manager.RelatedManager["Transaction"]

    telegram_id = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username = models.CharField(max_length=255, blank=True, verbose_name="Username")
    active_promo = models.ForeignKey(
        PromoCode,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="telegram_users",
        verbose_name="Актив. промокод"
    )
    promo_since = models.DateTimeField(null=True, blank=True, verbose_name="Дата активации промокода")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата регистрации")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

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
        metadata_info_id: int

    id = models.UUIDField(primary_key=True, verbose_name="ID платежа", help_text="Это ID из внешнего API")
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Покупатель"
    )
    amount_fiat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма", help_text="Со скидкой (если есть)")
    amount_stars = models.IntegerField(verbose_name="Количество звезд")
    target_username = models.CharField(max_length=255, blank=True, default=TARGET_SELF, verbose_name="Кому")
    status = models.CharField(max_length=20, choices=TransactionStatus.to_choices(), default=TransactionStatus.PENDING, verbose_name="Статус")
    message_id = models.IntegerField(default=-1, blank=True, verbose_name="ID сообщения заказа", help_text="Нужно для вебхука")
    pay_url = models.CharField(max_length=255, default="dummy.pay.link", verbose_name="URL оплаты", help_text="Приходит из платёжной системы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Истекает")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @override
    def __str__(self):
        return f"Транзакция #{self.id} ({self.telegram_user})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"


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
    promo_id = models.BigIntegerField(null=True, blank=True, verbose_name="ID промокода")
    promo_name = models.CharField(max_length=50, blank=True, verbose_name="Имя промокода")
    promo_discount = models.DecimalField(
        null=True, blank=True,
        decimal_places=2,
        max_digits=5,
        verbose_name="Скидка промокода %",
        help_text="Указывается в %, например, 5.00 (не 0.05)"
    )
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
    is_active = models.BooleanField(default=False, verbose_name="Активен?")

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


class FragmentTransaction(models.Model):
    objects = models.Manager()

    fragment_id = models.UUIDField(primary_key=True, verbose_name="ID Fragment")
    id_from_payment_api = models.UUIDField(verbose_name="ID из платёжного API")
    status = models.CharField(max_length=40, choices=FragmentStatus.to_choices(), default=FragmentStatus.CREATED, verbose_name="Статус FRAGMENT")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @override
    def __str__(self):
        return f"Транзакция Fragment #{self.fragment_id} (платёжное ID {self.id_from_payment_api})"

    class Meta:
        verbose_name = "Транзакция Fragment"
        verbose_name = "Транзакции Fragment"


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
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

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


class FragmentAPI(SingletonModel):
    objects = models.Manager()

    token = models.TextField(blank=True, help_text="Можно получить в Dashboard на fragment-api.com/dashboard")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    @classmethod
    async def aget_solo(cls):
        obj, is_created = await cls.objects.aget_or_create(pk=cls.singleton_instance_id)
        return obj

    @override
    def __str__(self):
        return "Токен для FragmentAPI"

    class Meta:
        verbose_name = "Токен для FragmentAPI"


# TODO: Вроде бы не надо, так как для Persistence будет PicklePersistence
class BotState(models.Model):
    objects = models.Manager()

    user_id = models.BigIntegerField(unique=True)
    data = models.JSONField(default=dict)
    state = models.TextField(null=True)
