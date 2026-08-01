from collections.abc import Awaitable, Callable


type AsyncCallable[**P,R] = Callable[P, Awaitable[R]]
