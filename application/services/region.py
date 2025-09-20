from typing import List
from api import ApiRegionDTO
from api.gateways import RegionGateway

class RegionService:
    def __init__(self, gateway: RegionGateway):
        self._gateway = gateway

    async def get_all_regions(self) -> List[ApiRegionDTO]:
        """Отримує всі регіони (часові пояси) з API."""
        response_data = await self._gateway.get_all_regions()
        if not response_data:
            return []
        return [ApiRegionDTO.model_validate(region) for region in response_data]