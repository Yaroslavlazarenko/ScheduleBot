from typing import Dict
from api import ApiCreateUserDTO, ApiUserDTO, ResourceNotFoundError
from api.gateways import UserGateway

class UserService:
    def __init__(self, gateway: UserGateway):
        self._gateway = gateway
        self._user_cache: Dict[int, ApiUserDTO] = {}

    async def get_user_by_telegram_id(self, telegram_id: int) -> ApiUserDTO | None:
        """Отримує користувача за telegram_id, використовуючи кеш."""
        if telegram_id in self._user_cache:
            return self._user_cache[telegram_id]

        try:
            user_data = await self._gateway.get_user_by_telegram_id(telegram_id)
            user_dto = ApiUserDTO.model_validate(user_data)
            
            self._user_cache[telegram_id] = user_dto
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