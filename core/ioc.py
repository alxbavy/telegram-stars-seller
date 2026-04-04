from dishka import Provider, Scope, provide
from core.services.star_price import StarService
from core.services.payment import PaymentService


class BusinessLogicProvider(Provider):
    pass
    # TODO: Uncomment services on stage when repositories have been created because of dishka MissingHintsError
    # star_service = provide(StarService, scope=Scope.APP)
    # payment_service = provide(PaymentService, scope=Scope.APP)
