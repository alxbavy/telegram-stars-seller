import os
import requests
import logging


logger = logging.getLogger(__name__)

class FragmentAPI:
    def __init__(self):
        self.url = os.getenv("FRAGMENT_API_URL")
        if not self.url:
            logger.error("FRAGMENT_API_URL не указан, перевод звёзд невозможен.")
            return
        # TODO: возможно пересмотреть поведение при ошибке
        self.token = None
        self.authenticate_fragment()

    def authenticate_fragment(self):
        env_vars = ["FRAGMENT_MNEMONICS", "FRAGMENT_API_KEY", "FRAGMENT_PHONE", "TON_WALLET_VERSION"]
        fragment_mnemonics = os.getenv(env_vars[0])
        fragment_api_key = os.getenv(env_vars[1])
        fragment_phone = os.getenv(env_vars[2])
        wallet_version = os.getenv(env_vars[3]) # TODO: узнать версию TON-кошелька у заказчиков
        fail = False
        for i, var in enumerate([fragment_mnemonics, fragment_api_key, fragment_phone, wallet_version]):
            if not var:
                logger.error(f"{env_vars[i]} не установлен. Аутентификация невозможна.")
                fail = True
        # TODO: возможно пересмотреть поведение при ошибке
        if fail:
            return

        try:
            mnemonics_list = fragment_mnemonics.strip().split()
            payload = {
                "api_key": fragment_api_key,
                "phone_number": fragment_phone,
                "mnemonics": mnemonics_list,
                "version": wallet_version
            }
            res = requests.post(f"{self.url}/auth/authenticate/", json=payload)
            if res.status_code == 200:
                self.token = res.json().get("token")
                return
            logger.error(f"Ошибка авторизации Fragment: {res.text}")
            return

        except Exception:
            logger.exception(f"Исключение при авторизации Fragment:")
            return


    async def send_stars(self, username: str, amount_stars: str):
        try:
            data = {
                "username": username,
                "quantity": amount_stars,
                "show_sender": "false"
            }
            headers = {
                "Authorization": f"JWT {self.token}",
                "Content-Type": "application/json"
            }

            res = requests.post(f"{self.url}/order/stars/", json=data, headers=headers)
            is_send_success = False
            if res.status_code == 200:
                is_send_success = True
            else:
                logger.error(f"Не удалось отправить звёзды: {res.text}")
            return is_send_success, res.text

        except Exception as e:
            logger.exception(f"Исключение при отправке:")
            return False, dict({"error": str(e)})
