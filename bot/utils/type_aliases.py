from typing import Concatenate

from telegram import Update
from telegram.ext import ContextTypes

from core.domain.type_aliases import AsyncCallable


type UpdateWithContextHandler[**P,R] = AsyncCallable[Concatenate[Update, ContextTypes.DEFAULT_TYPE, P], R]
type UpdateHandler[**P,R] = AsyncCallable[Concatenate[Update, P], R]
type ContextHandler[**P,R] = AsyncCallable[Concatenate[ContextTypes.DEFAULT_TYPE, P], R]
