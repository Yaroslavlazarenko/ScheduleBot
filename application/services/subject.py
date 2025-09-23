import time
from typing import List, Dict, Tuple
from api import ApiGroupedSubjectDTO, ApiGroupedSubjectDetailsDTO, ResourceNotFoundError
from api.gateways.subject_gateway import SubjectGateway
from .teacher import TeacherService

CACHE_TTL_SECONDS = 3600  # 1 година

class SubjectService:
    def __init__(self, gateway: SubjectGateway, teacher_service: TeacherService): # <--- Оновлюємо __init__
        self._gateway = gateway
        self._teacher_service = teacher_service
        self._subjects_list_cache: Tuple[List[ApiGroupedSubjectDTO], float] | None = None
        self._subject_details_cache: Dict[str, Tuple[ApiGroupedSubjectDetailsDTO, float]] = {}

    async def get_all_subjects(self) -> List[ApiGroupedSubjectDTO]:
        """Отримує список предметів, використовуючи кеш з TTL."""
        if self._subjects_list_cache is not None:
            data, timestamp = self._subjects_list_cache
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data 

        response_data = await self._gateway.get_all_subjects()
        if not response_data:
            return []
        
        subjects = [ApiGroupedSubjectDTO.model_validate(subject) for subject in response_data]
        
        self._subjects_list_cache = (subjects, time.time())
        return subjects

    async def get_grouped_subject_details(self, abbreviation: str) -> ApiGroupedSubjectDetailsDTO | None:
        """Отримує деталі про предмет, використовуючи кеш з TTL."""
        if abbreviation in self._subject_details_cache:
            data, timestamp = self._subject_details_cache[abbreviation]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        try:
            response_data = await self._gateway.get_grouped_subject_details_by_abbreviation(abbreviation)
            details = ApiGroupedSubjectDetailsDTO.model_validate(response_data)
            
            self._subject_details_cache[abbreviation] = (details, time.time())
            return details
        except ResourceNotFoundError:
            return None

    def format_subject_details(self, subject: ApiGroupedSubjectDetailsDTO) -> str:
        header = f"📚 <b>{subject.name} ({subject.abbreviation})</b>\n"
        parts = [header]

        if not subject.variants:
            parts.append("<i>Детальна інформація відсутня.</i>")
            return "\n".join(parts)

        for variant in subject.variants:
            parts.append(f"<b>━━━ {variant.subject_type.name} ━━━</b>")
            
            if variant.infos:
                info_parts = []
                for info in variant.infos:
                    if info.value and info.value.strip().lower().startswith("http"):
                        link = f"▫️ <a href='{info.value.strip()}'><b>{info.info_type_name}</b></a>"
                        info_parts.append(link)
                    else:
                        info_parts.append(f"▫️ <b>{info.info_type_name}:</b> {info.value}")
                parts.append("\n".join(info_parts))
            
            if not variant.teachers:
                parts.append("👨‍🏫 <i>Викладачі не призначені.</i>")
            else:
                teacher_lines = []
                for teacher in variant.teachers:
                    teacher_lines.append(f"• {teacher.full_name}")
                    
                    _, other_infos = self._teacher_service.extract_photo_and_infos(teacher)
                    
                    if other_infos:
                        for info in other_infos:
                            if info.value and info.value.strip().lower().startswith("http"):
                                link = f"    └ <a href='{info.value.strip()}'><b>{info.info_type_name}</b></a>"
                                teacher_lines.append(link)
                            else:
                                teacher_lines.append(f"    └ <b>{info.info_type_name}:</b> {info.value}")
                            
                parts.append(f"<b>Викладачі:</b>\n" + "\n".join(teacher_lines))
            
            parts.append("")

        return "\n".join(parts)