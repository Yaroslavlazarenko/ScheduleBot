from typing import Any
from api.client import ApiClient

class SubjectGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_subjects(self) -> Any:
        """Отримує всі згруповані предмети з API."""
        return await self._client.get('/api/Subject')

    async def get_grouped_subject_details_by_abbreviation(
        self, 
        abbreviation: str,
        group_id: int | None = None
    ) -> Any:
        """
        Отримує детальну інформацію про предмет за його абревіатурою.
        Якщо передано group_id, результат буде відфільтровано для цієї групи.
        """
        params = {}
        if group_id is not None:
            params['groupId'] = group_id
            
        return await self._client.get(f'/api/Subject/{abbreviation}', params=params)