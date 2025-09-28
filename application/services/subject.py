import time
from typing import List, Dict, Tuple
from api import ApiGroupedSubjectDTO, ApiGroupedSubjectDetailsDTO, ResourceNotFoundError
from api.gateways.subject_gateway import SubjectGateway
from .teacher import TeacherService

CACHE_TTL_SECONDS = 3600  # 1 година

class SubjectService:
    def __init__(self, gateway: SubjectGateway, teacher_service: TeacherService):
        self._gateway = gateway
        self._teacher_service = teacher_service
        self._subjects_list_cache: Tuple[List[ApiGroupedSubjectDTO], float] | None = None
        self._subject_details_cache: Dict[Tuple[int, int | None], Tuple[ApiGroupedSubjectDetailsDTO, float]] = {}

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

    async def get_grouped_subject_details(
        self, 
        subject_name_id: int, 
        group_id: int | None = None
    ) -> ApiGroupedSubjectDetailsDTO | None:
        """Отримує деталі про предмет за ID його назви, використовуючи кеш."""
        
        cache_key = (subject_name_id, group_id)
        if cache_key in self._subject_details_cache:
            data, timestamp = self._subject_details_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data

        try:
            response_data = await self._gateway.get_grouped_subject_details_by_id(subject_name_id, group_id)
            details = ApiGroupedSubjectDetailsDTO.model_validate(response_data)
            
            self._subject_details_cache[cache_key] = (details, time.time())
            return details
        except ResourceNotFoundError:
            return None

    def format_subject_details(self, subject: ApiGroupedSubjectDetailsDTO) -> str:
        header = f"📚 <b>{subject.name} ({subject.abbreviation})</b>"
        parts = [header]

        if not subject.variants:
            parts.append("<i>Детальна інформація відсутня.</i>")
            return "\n".join(parts)

        all_teachers = {teacher.id: teacher for variant in subject.variants for teacher in variant.teachers}

        if all_teachers:
            parts.append("\n<b>Викладачі курсу:</b>")
            teacher_lines = []
            for teacher in sorted(all_teachers.values(), key=lambda t: t.full_name):
                teacher_lines.append(f"• {teacher.full_name}")
                
                _, other_infos = self._teacher_service.extract_photo_and_infos(teacher)
                
                if other_infos:
                    for info in other_infos:
                        if info.value and info.value.strip().lower().startswith("http"):
                            link = f"    └ <a href='{info.value.strip()}'><b>{info.info_type_name}</b></a>"
                            teacher_lines.append(link)
                        else:
                            teacher_lines.append(f"    └ <b>{info.info_type_name}:</b> {info.value}")
            
            parts.append("\n".join(teacher_lines))
        
        parts.append("\n────────────────────\n")

        for variant in subject.variants:
            parts.append(f"<b>─── {variant.subject_type.name} ───</b>")
            
            if variant.infos:
                info_parts = []
                for info in variant.infos:
                    main_line = ""
                    if info.value and info.value.strip().lower().startswith("http"):
                        main_line = f"▫️ <a href='{info.value.strip()}'><b>{info.info_type_name}</b></a>"
                    else:
                        main_line = f"▫️ <b>{info.info_type_name}:</b> {info.value}"
                    info_parts.append(main_line)

                    if info.description:
                        info_parts.append(f"    └ <i>{info.description}</i>")
                parts.append("\n".join(info_parts))
            
            if not variant.teachers:
                parts.append("👨‍🏫 <i>Викладачі не призначені.</i>")
            else:
                teacher_names = ", ".join(sorted([t.full_name for t in variant.teachers]))
                parts.append(f"<i>Викладачі: {teacher_names}</i>")
            
            parts.append("")

        return "\n".join(parts)