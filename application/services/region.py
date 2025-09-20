from typing import List
from api import ApiClient, ApiRegionDTO

class RegionService:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_timezones(self) -> List[ApiRegionDTO]:
        """Отримує всі часові пояси з API."""
        response_data = await self._client.get('/api/region')
        if not response_data:
            return []
        return [ApiRegionDTO.model_validate(region) for region in response_data]