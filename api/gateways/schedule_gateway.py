from typing import Any
from api.client import ApiClient

class ScheduleGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_daily_schedule_for_group(
        self,
        group_id: int,
        time_zone_id: str,
        date: str | None = None
    ) -> Any:
        """Отримує розклад для групи, використовуючи groupId та timeZoneId."""
        params = {
            'groupId': group_id,
            'timeZoneId': time_zone_id
        }
        if date:
            params['date'] = date
        
        return await self._client.get('/api/schedule/group', params=params)
    
    async def get_weekly_schedule_for_group(
        self,
        group_id: int,
        time_zone_id: str,
        date: str | None = None
    ) -> Any:
        """Отримує розклад на тиждень для групи."""
        params = {
            'groupId': group_id,
            'timeZoneId': time_zone_id
        }
        if date:
            params['date'] = date
        
        return await self._client.get('/api/schedule/group/week', params=params)