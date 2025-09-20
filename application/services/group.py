from typing import List
from api import ApiGroupDTO
from api.gateways import GroupGateway

class GroupService:
    def __init__(self, gateway: GroupGateway):
        self._gateway = gateway

    async def get_all_groups(self) -> List[ApiGroupDTO]:
        """Отримує всі групи з API."""
        response_data = await self._gateway.get_all_groups()
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