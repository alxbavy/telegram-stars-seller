from django.conf import settings


class SupportService:
    @staticmethod
    async def get_support_url() -> str:
        return settings.SUPPORT_URL
