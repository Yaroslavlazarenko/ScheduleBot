import time
from typing import List, Tuple, Dict
from api import ApiTeacherDTO, ResourceNotFoundError
from api.gateways import TeacherGateway
from api import ApiTeacherInfoDTO

CACHE_TTL_SECONDS = 3600  # 1 година

class TeacherService:
    def __init__(self, gateway: TeacherGateway):
        self._gateway = gateway
        self._teachers_list_cache: Tuple[List[ApiTeacherDTO], float] | None = None
        self._teacher_details_cache: Dict[int, Tuple[ApiTeacherDTO, float]] = {}

    async def get_all_teachers(self) -> List[ApiTeacherDTO]:
        """Отримує список всіх викладачів, використовуючи кеш з TTL."""
        if self._teachers_list_cache is not None:
            data, timestamp = self._teachers_list_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        response_data = await self._gateway.get_all_teachers()
        if not response_data:
            self._teachers_list_cache = ([], time.time())
            return []
            
        teachers = [ApiTeacherDTO.model_validate(teacher) for teacher in response_data]
        self._teachers_list_cache = (teachers, time.time())
        return teachers

    async def get_teacher_by_id(self, teacher_id: int) -> ApiTeacherDTO | None:
        """Отримує деталі про викладача за його ID, використовуючи кеш з TTL."""
        if teacher_id in self._teacher_details_cache:
            data, timestamp = self._teacher_details_cache[teacher_id]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        try:
            response_data = await self._gateway.get_teacher_by_id(teacher_id)
            teacher = ApiTeacherDTO.model_validate(response_data)
            self._teacher_details_cache[teacher_id] = (teacher, time.time())
            return teacher
        except ResourceNotFoundError:
            return None

    def extract_photo_and_infos(self, teacher: ApiTeacherDTO) -> Tuple[str | None, List[ApiTeacherInfoDTO]]:
        """
        Витягує URL фотографії та решту інформації зі списку infos.
        Повертає кортеж (photo_url, other_infos).
        """
        photo_url = None
        other_infos = []
        for info in teacher.infos:
            if info.info_type_name.lower() == "photourl":
                photo_url = info.value
            else:
                other_infos.append(info)
        return photo_url, other_infos
    
    def format_teacher_details(self, teacher: ApiTeacherDTO, infos_to_display: List[ApiTeacherInfoDTO]) -> str:
        """
        Форматує детальну інформацію про викладача у повідомлення (без фото).
        """
        header = f"👨‍🏫 <b>{teacher.full_name}</b>\n"
        parts = [header]

        if not infos_to_display:
            parts.append("<i>Додаткова інформація відсутня.</i>")
        else:
            for info in infos_to_display:
                if info.value and info.value.strip().lower().startswith("http"):
                    link = f"<a href='{info.value.strip()}'><b>{info.info_type_name}</b></a>"
                    parts.append(link)
                else:
                    parts.append(f"<b>{info.info_type_name}:</b> {info.value}")

        return "\n".join(parts)