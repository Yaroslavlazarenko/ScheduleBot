from typing import Any
from api.client import ApiClient

class BroadcastGateway:
    def __init__(self, client: ApiClient):
        self._client = client

    async def create_broadcast(
        self,
        message_text: str,
        admin_api_key: str,
        scheduled_at: str | None = None
    ) -> Any:
        """Створює нове завдання на розсилку з заданим текстом та, можливо, часом."""
        data = {'messageText': message_text}
        if scheduled_at:
            data['scheduledAt'] = scheduled_at
        
        headers = {'X-Admin-Api-Key': admin_api_key}
        
        return await self._client.post('/api/broadcast', data=data, extra_headers=headers)