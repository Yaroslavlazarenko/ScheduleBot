from typing import Any
from api.client import ApiClient

class RegionGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_regions(self) -> Any:
        """Отримує всі регіони з API."""
        return await self._client.get('/api/Region')