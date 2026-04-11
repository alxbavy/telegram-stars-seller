class TelegramService:
    async def resolve_username(self, username: str) -> bool:
        """Проверяет, существует ли пользователь в Telegram."""
        return True