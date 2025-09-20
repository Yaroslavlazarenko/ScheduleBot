from typing import List
from api import ApiClient, ApiGroupDTO

class GroupService:
    def __init__(self, client: ApiClient):
        self._client = client

    async def get_all_groups(self) -> List[ApiGroupDTO]:
        """Отримує всі групи з API."""
        response_data = await self._client.get('/api/group')
        if not response_data:
            return []
        return [ApiGroupDTO.model_validate(group) for group in response_data]

    async def format_groups_list(self) -> str:
        """
        Отримує та форматує список груп для відображення користувачу.
        """
        groups = await self.get_all_groups()
        if not groups:
            return 'Список груп порожній.'

        header = "<b>Список доступних груп:</b>\n\n"
        body = "\n".join(f"• <code>{group.name}</code> (ID: <code>{group.id}</code>)" for group in groups)
        return header + body