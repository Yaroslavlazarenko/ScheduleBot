from api import ApiClient, ApiCreateUserDTO

class UserService:
    def __init__(self, client: ApiClient):
        self._client = client

    async def register_new_user(self, telegram_id: int, username: str | None, group_id_str: str, region_id_str: str) -> str:
        """
        Реєструє нового користувача.
        Викидає винятки у разі помилок валідації або API.
        """
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

        await self._client.post('/api/User', data=user_dto.model_dump(by_alias=True))
        return f"✅ Вас успішно зареєстровано!"