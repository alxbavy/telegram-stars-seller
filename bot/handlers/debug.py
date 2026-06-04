import json

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from bot.utils.injector import inject
from core.integrations.fragment.client import FragmentClient


@inject
async def _balance_handler_helper(update: Update, context: ContextTypes.DEFAULT_TYPE, fragment_client: FragmentClient) -> None:
    balance = await fragment_client.get_wallet_balance()
    text = f"<pre>{json.dumps(balance, indent=2, ensure_ascii=False)}</pre>"
    _ = await update.effective_user.send_message(text, parse_mode=ParseMode.HTML)


async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _balance_handler_helper(update, context)


@inject
async def _prices_handler_helper(update: Update, context: ContextTypes.DEFAULT_TYPE, fragment_client: FragmentClient) -> None:
    prices = await fragment_client.get_current_prices()
    text = f"<pre>{json.dumps(prices, indent=2, ensure_ascii=False)}</pre>"
    _ = await update.effective_user.send_message(text, parse_mode=ParseMode.HTML)


async def prices_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _prices_handler_helper(update, context)
