from bot.utils.type_aliases import AsyncCallable


def build_async_handlers_register[K](registry: dict[K, AsyncCallable[...,...]]):
    """
    Принимает словарь, в который будут регистрироваться функции по переданному ключу.

    Возвращает декоратор, который может принимать ключ/ключи, чтобы по ним зарегистрировать функцию, например::

        register = build_async_handlers_register(some_registry)
        @register(key) или для нескольких ключей @register(key1, key2)
        async def my_handler(...) -> R: ...

    Регистрируемая функция может принимать любые аргументы. Какие именно должны быть эти аргументы, и что должно быть
    возвращено, зависит от того, какая аннотация указана у переданного словаря для значений пар.
    """
    def decorator_for_key_input(*keys: K):
        """
        Это декоратор, который может принимать ключ/ключи, чтобы по ним зарегистрировать функцию, например::

            register = build_async_handlers_register(some_registry)
            @register(key) или для нескольких ключей @register(key1, key2)
            async def my_handler(...) -> R: ...

        Регистрируемая функция может принимать любые аргументы. Какие именно должны быть эти аргументы, и что должно быть
        возвращено, зависит от того, какая аннотация указана у переданного словаря для значений пар.
        """
        def decorator_for_handler_input[**P,R](func: AsyncCallable[P,R]):
            for key in keys:
                registry[key] = func
            return func
        return decorator_for_handler_input


    return decorator_for_key_input

