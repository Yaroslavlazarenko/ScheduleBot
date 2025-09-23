from typing import Any
from api.client import ApiClient

class SemesterGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_semesters(self) -> Any:
        """Отримує всі семестри з API."""
        return await self._client.get('/api/Semester')