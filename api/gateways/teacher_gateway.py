from typing import Any
from api.client import ApiClient

class TeacherGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_teachers(self) -> Any:
        """Отримує всіх викладачів з API."""
        return await self._client.get('/api/Teacher')

    async def get_teacher_by_id(self, teacher_id: int) -> Any:
        """Отримує викладача за його ID."""
        return await self._client.get(f'/api/Teacher/{teacher_id}')