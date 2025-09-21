import time
from typing import Dict, Tuple
from api import ApiCreateUserDTO, ApiUserDTO, ResourceNotFoundError
from api.gateways import UserGateway

CACHE_TTL_SECONDS = 3600  # 1 година

class UserService:
    def __init__(self, gateway: UserGateway):
        self._gateway = gateway
        self._user_cache: Dict[int, Tuple[ApiUserDTO, float]] = {}

    async def get_user_by_telegram_id(self, telegram_id: int) -> ApiUserDTO | None:
        """Отримує користувача за telegram_id, використовуючи кеш з TTL."""
        if telegram_id in self._user_cache:
            user_dto, timestamp = self._user_cache[telegram_id]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return user_dto

        try:
            user_data = await self._gateway.get_user_by_telegram_id(telegram_id)
            user_dto = ApiUserDTO.model_validate(user_data)
            
            self._user_cache[telegram_id] = (user_dto, time.time())
            return user_dto
            
        except ResourceNotFoundError:
            return None

    async def register_new_user(self, telegram_id: int, username: str | None, group_id_str: str, region_id_str: str) -> str:
        """Реєструє нового користувача."""
        try:
            group_id = int(group_id_str)
            region_id = int(region_id_str)
        except (ValueError, TypeError):
            raise ValueError("❌ ID групи та часового поясу мають бути цілими числами.")

        user_dto = ApiCreateUserDTO(
            telegramId=telegram_id,
            username=username,
            groupId=group_id,
            regionId=region_id,
            isAdmin=False
        )

        await self._gateway.create_user(user_data=user_dto.model_dump(by_alias=True))

        return f"✅ Вас успішно зареєстровано!"

    async def change_user_group(self, telegram_id: int, new_group_id: int) -> None:
        """Змінює групу для користувача та інвалідує кеш."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Користувача не знайдено. Будь ласка, зареєструйтесь: /start")
        
        await self._gateway.change_user_group(user_id=user.id, new_group_id=new_group_id)

        if telegram_id in self._user_cache:
            del self._user_cache[telegram_id]

    async def change_user_region(self, telegram_id: int, new_region_id: int) -> None:
        """Змінює регіон для користувача та інвалідує кеш."""
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Користувача не знайдено. Будь ласка, зареєструйтесь: /start")
        
        await self._gateway.change_user_region(user_id=user.id, new_region_id=new_region_id)

        if telegram_id in self._user_cache:
            del self._user_cache[telegram_id]