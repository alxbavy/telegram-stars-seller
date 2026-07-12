import json
from typing import overload

from dishka import FromDishka

from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.base import send_new_message

from core.integrations.fragment.client import FragmentClient
from core.ioc import inject


@overload
async def _balance_handler_helper(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: Update,
        *,
        debug: bool
) -> None: ...


@inject
async def _balance_handler_helper(
        update: Update,
        *,
        debug: bool,
        fragment_client: FromDishka[FragmentClient]
) -> None:
    balance = await fragment_client.get_wallet_balances(debug)
    text = f"<pre>{json.dumps(balance, indent=2, ensure_ascii=False)}</pre>"
    _ = await send_new_message(update, text, reply_markup=None, photo_name=None)


async def balance_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    return await _balance_handler_helper(update, debug=False)


async def balance_handler_debug(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    return await _balance_handler_helper(update, debug=True)


@overload
async def _prices_handler_helper(  # noqa  # pyright: ignore[reportInconsistentOverload]
        update: Update,
        *,
        debug: bool
) -> None: ...


@inject
async def _prices_handler_helper(
        update: Update,
        *,
        debug: bool,
        fragment_client: FromDishka[FragmentClient]
) -> None:
    prices = await fragment_client.get_current_prices(debug)
    text = f"<pre>{json.dumps(prices, indent=2, ensure_ascii=False)}</pre>"
    _ = await send_new_message(update, text, reply_markup=None, photo_name=None)


async def prices_handler(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    return await _prices_handler_helper(update, debug=False)


async def prices_handler_debug(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    return await _prices_handler_helper(update, debug=True)
