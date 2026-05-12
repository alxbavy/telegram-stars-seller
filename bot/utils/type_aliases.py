from collections.abc import Awaitable, Callable
from typing import Concatenate

from telegram import Update
from telegram.ext import ContextTypes


type AsyncCallable[**P,R] = Callable[P, Awaitable[R]]
type UpdateWithContextHandler[**P,R] = AsyncCallable[Concatenate[Update, ContextTypes.DEFAULT_TYPE, P], R]
type UpdateHandler[**P,R] = AsyncCallable[Concatenate[Update, P], R]
