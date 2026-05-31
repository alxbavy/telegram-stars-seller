from typing import final
from dishka import Provider, Scope, provide

from core.integrations.fragment import FragmentClient
from core.integrations.platega import PlategaClient
from core.repositories.payment import PaymentRepository
from core.repositories.transaction import TransactionRepository
from core.repositories.user import UserRepository
from core.services.star_price import StarService
from core.services.payment import PaymentService
from core.services.stats import StatsService
from core.services.support import SupportService
from core.services.user import UserService


@final
class BusinessLogicProvider(Provider):
    payment_repo = provide(PaymentRepository, scope=Scope.APP)
    trans_repo = provide(TransactionRepository, scope=Scope.APP)
    user_repo = provide(UserRepository, scope=Scope.APP)

    fragment_client = provide(FragmentClient, scope=Scope.APP)
    platega_client = provide(PlategaClient, scope=Scope.APP)

    support_service = provide(SupportService, scope=Scope.APP)
    stats_service = provide(StatsService, scope=Scope.APP)
    star_service = provide(StarService, scope=Scope.APP)
    payment_service = provide(PaymentService, scope=Scope.APP)
    user_service = provide(UserService, scope=Scope.APP)
