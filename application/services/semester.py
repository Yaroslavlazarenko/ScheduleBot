import time
from datetime import date
from typing import List, Tuple

from api.dto import ApiSemesterDTO
from api.gateways import SemesterGateway

CACHE_TTL_SECONDS = 3600  # 1 година

class SemesterService:
    def __init__(self, gateway: SemesterGateway):
        self._gateway = gateway
        self._semesters_cache: Tuple[List[ApiSemesterDTO], float] | None = None

    async def get_all_semesters(self) -> List[ApiSemesterDTO]:
        """Отримує всі семестри з API, використовуючи кеш з TTL."""
        if self._semesters_cache is not None:
            data, timestamp = self._semesters_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        response_data = await self._gateway.get_all_semesters()
        if not response_data:
            self._semesters_cache = ([], time.time())
            return []
        
        semesters = [ApiSemesterDTO.model_validate(semester) for semester in response_data]
        self._semesters_cache = (semesters, time.time())
        return semesters

    async def get_current_semester(self) -> ApiSemesterDTO | None:
        """
        Знаходить поточний семестр (той, що включає сьогоднішню дату).
        Якщо такого немає, повертає найближчий майбутній або останній минулий.
        """
        semesters = await self.get_all_semesters()
        if not semesters:
            return None

        today = date.today()
        current_semester = None
        
        for semester in semesters:
            start_date = date.fromisoformat(semester.start_date.split('T')[0])
            end_date = date.fromisoformat(semester.end_date.split('T')[0])
            if start_date <= today <= end_date:
                current_semester = semester
                break
        
        if not current_semester and semesters:
            return max(semesters, key=lambda s: s.start_date)

        return current_semester