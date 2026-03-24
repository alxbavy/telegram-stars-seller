class BotStateRepository:
    async def get_all_states(self):
        return [state async for state in BotState.objects.all()]

    async def update_user_data(self, user_id: int, data: dict):
        await BotState.objects.aupdate_or_create(
            user_id=user_id,
            defaults={'data': data}
        )

    async def update_conversation(self, user_id: int, state: str | None):
        await BotState.objects.aupdate_or_create(
            user_id=user_id,
            defaults={'state': state}
        )

    async def get_conversations_with_state(self):
        # Фильтруем тех, у кого есть активное состояние
        qs = BotState.objects.exclude(state__isnull=True)
        return [state async for state in qs]