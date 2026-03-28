from asgiref.sync import sync_to_async


class UserRepository:
    @sync_to_async(thread_sensitive=True)
    def create_telegram_user(self, telegram_id, username):
        ...

    @sync_to_async(thread_sensitive=True)
    def get_by_telegram_id(self, telegram_id):
        ...

    @sync_to_async(thread_sensitive=True)
    def get_by_username(self, username):
        ...

    @sync_to_async(thread_sensitive=True)
    def get_many_by_date_period(self):
        ...

    @sync_to_async(thread_sensitive=True)
    def delete_user(self, user):
        ...
