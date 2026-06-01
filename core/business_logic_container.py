from dishka import make_async_container
from core.ioc import BusinessLogicProvider

container = make_async_container(BusinessLogicProvider())
