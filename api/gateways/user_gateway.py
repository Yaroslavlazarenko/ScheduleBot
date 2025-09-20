from typing import Any
from api.client import ApiClient

class UserGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_user_by_telegram_id(self, telegram_id: int) -> Any:
        """Отримує користувача за його Telegram ID."""
        return await self._client.get(f'/api/User/telegram/{telegram_id}')

    async def get_schedule_for_user(self, user_id: int, date: str | None = None) -> Any:
        """Отримує розклад для користувача на конкретну дату."""
        params = {}
        if date:
            params['date'] = date
        return await self._client.get(f'/api/User/{user_id}/schedule', params=params)
    
    async def create_user(self, user_data: dict) -> Any:
        """Створює нового користувача."""
        return await self._client.post('/api/User', data=user_data)