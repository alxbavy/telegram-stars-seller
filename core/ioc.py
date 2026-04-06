from dishka import Provider, Scope, provide

from bot.stubs import SupportService, TelegramApiService, StatsService
from core.services.star_price import StarService
from core.services.payment import PaymentService


class BusinessLogicProvider(Provider):
    support_service = provide(SupportService, scope=Scope.APP)
    tg_api_service = provide(TelegramApiService, scope=Scope.APP)
    stats_service = provide(StatsService, scope=Scope.APP)
    star_service = provide(StarService, scope=Scope.APP)
    payment_service = provide(PaymentService, scope=Scope.APP)
