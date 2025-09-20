from typing import List, Dict
from api import ApiRegionDTO
from api.gateways import RegionGateway

class RegionService:
    def __init__(self, gateway: RegionGateway):
        self._gateway = gateway
        self._regions_cache: List[ApiRegionDTO] | None = None
        self._region_map_cache: Dict[int, str] | None = None

    async def get_all_regions(self) -> List[ApiRegionDTO]:
        """Отримує всі регіони, використовуючи кеш."""
        if self._regions_cache is not None:
            return self._regions_cache

        response_data = await self._gateway.get_all_regions()
        if not response_data:
            return []
        
        regions_dtos = [ApiRegionDTO.model_validate(region) for region in response_data]
        
        self._regions_cache = regions_dtos
        return regions_dtos

    async def get_timezone_by_id(self, region_id: int) -> str | None:
        """
        Швидко знаходить time_zone_id для регіону за його ID, використовуючи кеш.
        """
        if self._regions_cache is None:
            await self.get_all_regions()
        
        if self._region_map_cache is None and self._regions_cache:
            self._region_map_cache = {region.id: region.time_zone_id for region in self._regions_cache}
        
        if self._region_map_cache:
            return self._region_map_cache.get(region_id)
        
        return None