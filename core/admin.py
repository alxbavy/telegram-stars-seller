from django.contrib import admin
from django.utils import timezone
from django.utils.formats import localize
from solo.admin import SingletonModelAdmin
from .models import (
    TelegramUser, Transaction, TransactionMetadata,
    PaymentMethod, GlobalSettings, ExchangeRate
)


# --- ИНЛАЙНЫ ---

class TransactionInline(admin.TabularInline):
    """Инлайн для отображения транзакций в карточке пользователя"""
    model = Transaction
    readonly_fields = ('amount_stars', 'amount_fiat', 'status', 'created_at', 'updated_at')
    show_change_link = True
    can_delete = False
    ordering = ('-created_at',)
    verbose_name = "История транзакций"
    verbose_name_plural = "История транзакций"

    def has_add_permission(self, request, obj=None):
        return False


class TransactionMetadataInline(admin.StackedInline):
    model = TransactionMetadata
    can_delete = False


# --- АДМИН-КЛАССЫ ---

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'telegram_id', 'created_at')
    search_fields = ('username', 'telegram_id')
    list_filter = (('created_at', admin.DateFieldListFilter),)
    search_help_text = 'Поиск по имени пользователя или ID'
    readonly_fields = ('created_at',)
    inlines = [TransactionInline]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_user', 'amount_stars', 'amount_fiat', 'status', 'created_at', 'updated_at')
    list_filter = ('status', ('created_at', admin.DateFieldListFilter), ('updated_at', admin.DateFieldListFilter))
    search_fields = ('telegram_user__username', 'telegram_user__telegram_id')
    search_help_text = 'Поиск по имени пользователя или ID'
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TransactionMetadataInline]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'commission_percent', 'is_active')
    list_editable = ('commission_percent', 'is_active')


@admin.register(GlobalSettings)
class GlobalSettingsAdmin(SingletonModelAdmin):
    # Добавляем отображение полей из ExchangeRate прямо сюда с помощью "виртуальных" полей
    readonly_fields = ('usd_current_rate_display', 'last_usd_rate_update_display')

    fieldsets = (
        ('Основные настройки цены', {
            'fields': ('star_base_cost', 'usd_base_rate', 'is_use_usd_rate')
        }),
        ('Текущие рыночные данные', {
            'fields': ('usd_current_rate_display', 'last_usd_rate_update_display'),
            'description': 'Эти данные обновляются автоматически и используются для расчета, если включена опция выше.'
        }),
        ('Статус бота', {
            'fields': ('maintenance_mode',),
        }),
    )

    def usd_current_rate_display(self, obj):
        return ExchangeRate.get_solo().usd_rate

    usd_current_rate_display.short_description = "Текущий курс доллара"

    def last_usd_rate_update_display(self, obj):
        return localize(timezone.template_localtime(ExchangeRate.get_solo().updated_at))


    last_usd_rate_update_display.short_description = "Дата последнего обновления курса"
