class UserService:
    '''def __init__(self, user_repo, trans_repo):
        self.user_repo = user_repo
        self.trans_repo = trans_repo'''

    async def get_profile_data(self, user_id: int):
        user = await self.user_repo.get_or_create(user_id)
        stats = await self.trans_repo.get_user_stats(user_id)
        return # ToDo: UserProfileDTO
