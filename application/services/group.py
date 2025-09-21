import time
from typing import List, Tuple
from api import ApiGroupDTO
from api.gateways import GroupGateway

CACHE_TTL_SECONDS = 3600  # 1 година

class GroupService:
    def __init__(self, gateway: GroupGateway):
        self._gateway = gateway
        self._groups_cache: Tuple[List[ApiGroupDTO], float] | None = None

    async def get_all_groups(self) -> List[ApiGroupDTO]:
        """Отримує всі групи з API, використовуючи кеш з TTL."""
        if self._groups_cache is not None:
            data, timestamp = self._groups_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        response_data = await self._gateway.get_all_groups()
        if not response_data:
            self._groups_cache = ([], time.time()) # Кешуємо пустий результат
            return []
        
        groups = [ApiGroupDTO.model_validate(group) for group in response_data]
        self._groups_cache = (groups, time.time())
        return groups

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