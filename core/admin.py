from collections.abc import Mapping
import json
from decimal import Decimal
from typing import final, override

from django import forms
from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest
from django.utils import timezone
from django.utils.formats import localize
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from solo.admin import SingletonModelAdmin

from .models import (
    PaymentAPI, TelegramUser, Transaction, TransactionMetadata,
    PaymentMethod, GlobalSettings, ExchangeRate, FragmentAPI,
    MonthlyProfit
)


class TransactionTypeMixin:
    def transaction_type(self, obj: Transaction) -> str:
        """Достаем человекочитаемое название типа из связанной модели"""
        try:
            return obj.metadata_info.get_type_display()
        except TransactionMetadata.DoesNotExist:
            return "—"
    transaction_type.short_description = "Тип"
    transaction_type.admin_order_field = "metadata_info__type"


@final
class TransactionInline(admin.TabularInline, TransactionTypeMixin):
    """Инлайн для отображения транзакций в карточке пользователя"""
    model: type[Transaction] = Transaction
    readonly_fields = ("id", "target_username", "amount_stars", "amount_fiat",
                       "status", "transaction_type", "created_at", "expires_at", "updated_at")
    show_change_link = True
    can_delete = False
    ordering = ("-created_at",)
    verbose_name = "История транзакций"
    verbose_name_plural = "История транзакций"

    @override
    def has_add_permission(self, request: HttpRequest, obj: object | None = None):
        return False


@final
@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("username", "telegram_id", "created_at")
    search_fields = ("username", "telegram_id")
    list_filter = (("created_at", admin.DateFieldListFilter),)
    search_help_text = "Поиск по имени пользователя или ID"
    if settings.DEBUG:
        readonly_fields = ("created_at",)
    else:
        readonly_fields = ("username", "telegram_id", "created_at")
    inlines = [TransactionInline]


class PrettyJSONWidget(forms.Textarea):
    @override
    def format_value(self, value: str | Mapping[str, object]):
        try:
            if isinstance(value, str):
                value = json.loads(value)
            return json.dumps(value, indent=4, ensure_ascii=False)
        except (ValueError, TypeError):
            return super().format_value(value)


@final
class TransactionMetadataInline(admin.StackedInline):
    model: type[TransactionMetadata] = TransactionMetadata
    can_delete = False
    formfield_overrides = {
        TransactionMetadata._meta.get_field(
            "payload"
        ).__class__: {"widget": PrettyJSONWidget}
    }


@final
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin, TransactionTypeMixin):
    list_display = ("id", "telegram_user", "amount_stars", "amount_fiat", "target_username",
                    "status", "transaction_type", "created_at", "expires_at", "updated_at")
    ordering = ("-created_at",)
    list_filter = (
        "status", ("created_at", admin.DateFieldListFilter), ("updated_at", admin.DateFieldListFilter),
        ("expires_at", admin.DateFieldListFilter)
    )
    search_fields = ("telegram_user__username", "telegram_user__telegram_id")
    search_help_text = "Поиск по имени пользователя или ID"
    readonly_fields = ("created_at", "expires_at", "updated_at")
    readonly_fields_when_created = ("id",)
    inlines = [TransactionMetadataInline]

    @override
    def get_readonly_fields(self, request: HttpRequest, obj: Transaction | None = None):
        if obj:
            return tuple(list(self.readonly_fields) + list(self.readonly_fields_when_created))

        return tuple(self.readonly_fields)


@final
class PaymentMethodInline(admin.TabularInline):
    model: type[PaymentMethod] = PaymentMethod
    list_display = ("name", "commission_percent", "external_id", "is_active")
    extra = 0


@final
@admin.register(PaymentAPI)
class PaymentAPIAdmin(admin.ModelAdmin):
    inlines = [PaymentMethodInline]
    list_display = ("name", )


@final
@admin.register(GlobalSettings)
class GlobalSettingsAdmin(SingletonModelAdmin):
    # Добавляем отображение полей из ExchangeRate прямо сюда с помощью "виртуальных" полей
    readonly_fields = ("usd_current_rate_display", "last_usd_rate_update_display")

    fieldsets = (
        ("Основные настройки цены", {
            "fields": ("star_base_cost", "usd_base_rate", "is_use_usd_rate")
        }),
        ("Текущие рыночные данные", {
            "fields": ("usd_current_rate_display", "last_usd_rate_update_display"),
            "description": "Эти данные обновляются автоматически и используются для расчета, если включена опция выше."
        }),
        ("Статус бота", {
            "fields": ("maintenance_mode",),
        }),
    )

    def usd_current_rate_display(self, obj: object) -> Decimal:
        return ExchangeRate.get_solo().usd_rate

    usd_current_rate_display.short_description = "Текущий курс доллара"

    def last_usd_rate_update_display(self, obj: object) -> str:
        return localize(timezone.template_localtime(ExchangeRate.get_solo().updated_at))

    last_usd_rate_update_display.short_description = "Дата последнего обновления курса"


@final
@admin.register(MonthlyProfit)
class MonthlyProfitAdmin(admin.ModelAdmin):
    # Кастомный шаблон
    change_list_template = "admin/monthly_profit_report.html"

    @override
    def changelist_view(self, request: HttpRequest, extra_context: dict[str, str] | None = None):
        # 1. Берем только успешные транзакции
        # 2. Группируем (TruncMonth) по месяцу создания
        # 3. Суммируем поле amount_fiat
        monthly_stats = (
            Transaction.objects.filter(status="SUCCESS")
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total_profit=Sum("amount_fiat"))
            .order_by("-month")
        )

        total_all_time = (
            Transaction.objects
            .filter(status="SUCCESS")
            .aggregate(Sum("amount_fiat"))["amount_fiat__sum"] or 0
        )

        extra_context = extra_context or {}
        extra_context["title"] = "Отчет по прибыли по месяцам"
        extra_context["monthly_stats"] = monthly_stats
        extra_context["total_all_time"] = total_all_time

        return super().changelist_view(request, extra_context=extra_context)

    # Запрещаем любые действия, кроме просмотра
    @override
    def has_add_permission(self, request: HttpRequest): return False
    @override
    def has_delete_permission(self, request: HttpRequest, obj: object | None = None): return False
    @override
    def has_change_permission(self, request: HttpRequest, obj: object | None = None): return False


@final
@admin.register(FragmentAPI)
class FragmentAPIAdmin(SingletonModelAdmin):
    list_display = ("token", "updated_at")
    readonly_fields = ("updated_at", )
