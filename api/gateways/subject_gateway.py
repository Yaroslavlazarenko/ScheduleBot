from typing import Any
from api.client import ApiClient

class SubjectGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_subjects(self) -> Any:
        """Отримує всі згруповані предмети з API."""
        return await self._client.get('/api/Subject')

    async def get_grouped_subject_details_by_id(
        self, 
        subject_name_id: int,
        group_id: int | None = None
    ) -> Any:
        params = {'groupId': group_id} if group_id else None
            
        return await self._client.get(f'/api/Subject/by-name-id/{subject_name_id}/info', params=params)