from dataclasses import dataclass


@dataclass
class UserProfileDTO:
    telegram_id: int
    purchases_count: int
    stars_bought: int
