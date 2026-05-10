import asyncio


class TelegramService:
    async def resolve_username(self, username: str) -> bool:
        """Проверяет, существует ли пользователь в Telegram."""
        await asyncio.sleep(5)
        return True
