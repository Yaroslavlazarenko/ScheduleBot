import time
from typing import List, Dict, Tuple
from api import ApiRegionDTO
from api.gateways import RegionGateway

CACHE_TTL_SECONDS = 3600  # 1 година

class RegionService:
    def __init__(self, gateway: RegionGateway):
        self._gateway = gateway
        self._regions_cache: Tuple[List[ApiRegionDTO], float] | None = None
        self._region_map_cache: Dict[int, str] | None = None

    async def get_all_regions(self) -> List[ApiRegionDTO]:
        """Отримує всі регіони, використовуючи кеш з TTL."""
        if self._regions_cache is not None:
            data, timestamp = self._regions_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        response_data = await self._gateway.get_all_regions()
        if not response_data:
            self._regions_cache = ([], time.time())
            self._region_map_cache = {}
            return []
        
        regions_dtos = [ApiRegionDTO.model_validate(region) for region in response_data]
        
        self._regions_cache = (regions_dtos, time.time())
        self._region_map_cache = None
        return regions_dtos

    async def get_timezone_by_id(self, region_id: int) -> str | None:
        """
        Швидко знаходить time_zone_id для регіону за його ID, використовуючи кеш.
        """
        regions = await self.get_all_regions()
        
        if self._region_map_cache is None and regions:
            self._region_map_cache = {region.id: region.time_zone_id for region in regions}
        
        if self._region_map_cache:
            return self._region_map_cache.get(region_id)
        
        return None