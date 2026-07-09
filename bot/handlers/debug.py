import json

from telegram import Update
from telegram.ext import ContextTypes

from bot.renderers.base import send_new_message
from bot.utils.injector import inject

from core.integrations.fragment.client import FragmentClient


@inject
async def _balance_handler_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        debug: bool,
        fragment_client: FragmentClient
) -> None:
    balance = await fragment_client.get_wallet_balances(debug)
    text = f"<pre>{json.dumps(balance, indent=2, ensure_ascii=False)}</pre>"
    _ = await send_new_message(update, text, reply_markup=None, photo_name=None)


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _balance_handler_helper(update, context, debug=False)


async def balance_handler_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _balance_handler_helper(update, context, debug=True)


@inject
async def _prices_handler_helper(
        update: Update, context: ContextTypes.DEFAULT_TYPE,
        debug: bool,
        fragment_client: FragmentClient
) -> None:
    prices = await fragment_client.get_current_prices(debug)
    text = f"<pre>{json.dumps(prices, indent=2, ensure_ascii=False)}</pre>"
    _ = await send_new_message(update, text, reply_markup=None, photo_name=None)


async def prices_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _prices_handler_helper(update, context, debug=False)


async def prices_handler_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _prices_handler_helper(update, context, debug=True)
