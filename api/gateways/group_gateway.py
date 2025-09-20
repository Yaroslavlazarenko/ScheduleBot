from typing import Any
from api.client import ApiClient

class GroupGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_groups(self) -> Any:
        """Отримує всі групи з API."""
        return await self._client.get('/api/group')