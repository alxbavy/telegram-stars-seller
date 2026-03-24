from telegram.ext import BasePersistence, PersistenceInput
from core.repositories.bot_state_repo import BotStateRepository

class AsyncDjangoPersistence(BasePersistence):
    def __init__(self, repo: BotStateRepository):
        store_data = PersistenceInput(user_data=True, bot_data=False, chat_data=False)
        super().__init__(store_data=store_data)
        self.repo = repo

    async def get_user_data(self) -> dict[int, dict]:
        states = await self.repo.get_all_states()
        return {s.user_id: s.data for s in states}

    async def update_user_data(self, user_id: int, data: dict) -> None:
        await self.repo.update_user_data(user_id, data)

    async def get_conversations(self, name: str) -> dict:
        states = await self.repo.get_conversations_with_state()
        return {(s.user_id, s.user_id): s.state for s in states}

    async def update_conversation(self, name: str, key: tuple, new_state: str | None) -> None:
        user_id = key[0]
        await self.repo.update_conversation(user_id, new_state)

    # Остальные методы (bot_data, chat_data, callback_data)
    # реализуем пустыми, если они не нужны в MVP
    async def get_bot_data(self) -> dict: return {}
    async def update_bot_data(self, data: dict) -> None: pass
    async def get_chat_data(self) -> dict: return {}
    async def update_chat_data(self, chat_id: int, data: dict) -> None: pass
    async def get_callback_data(self) -> dict: return None
    async def update_callback_data(self, data: dict) -> None: pass
    async def flush(self) -> None: pass