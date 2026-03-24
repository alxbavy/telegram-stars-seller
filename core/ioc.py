from dishka import Provider, Scope, provide
from core.repositories.user_repo import UserRepository
from core.repositories.trans_repo import TransactionRepository
from core.repositories.settings_repo import SettingsRepository
from core.services.star_service import StarService
from core.services.payment_service import PaymentService


class BusinessLogicProvider(Provider):
    user_repo = provide(UserRepository, scope=Scope.APP)
    trans_repo = provide(TransactionRepository, scope=Scope.APP)
    settings_repo = provide(SettingsRepository, scope=Scope.APP)

    star_service = provide(StarService, scope=Scope.APP)
    payment_service = provide(PaymentService, scope=Scope.APP)