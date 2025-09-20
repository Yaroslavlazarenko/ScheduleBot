from typing import List, Tuple
from api import ApiTeacherDTO, ResourceNotFoundError
from api.gateways import TeacherGateway
from api import ApiTeacherInfoDTO

class TeacherService:
    def __init__(self, gateway: TeacherGateway):
        self._gateway = gateway

    async def get_all_teachers(self) -> List[ApiTeacherDTO]:
        """Отримує список всіх викладачів."""
        response_data = await self._gateway.get_all_teachers()
        if not response_data:
            return []
        return [ApiTeacherDTO.model_validate(teacher) for teacher in response_data]

    async def get_teacher_by_id(self, teacher_id: int) -> ApiTeacherDTO | None:
        """Отримує деталі про викладача за його ID."""
        try:
            response_data = await self._gateway.get_teacher_by_id(teacher_id)
            return ApiTeacherDTO.model_validate(response_data)
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
                parts.append(f"<b>{info.info_type_name}:</b> {info.value}")

        return "\n".join(parts)