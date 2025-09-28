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
    
    async def get_pending_broadcast(self, admin_api_key: str) -> Any:
        """Отримує одне активне завдання на розсилку, яке ще не було надіслано."""
        headers = {'X-Admin-Api-Key': admin_api_key}
        return await self._client.get('/api/notification/pending-broadcast', extra_headers=headers)
    
    async def mark_broadcast_as_sent(self, broadcast_id: int, admin_api_key: str) -> None:
        """Позначає завдання на розсилку як виконане."""
        headers = {'X-Admin-Api-Key': admin_api_key}
        await self._client.post(f'/api/notification/broadcast/{broadcast_id}/sent', data={}, extra_headers=headers)