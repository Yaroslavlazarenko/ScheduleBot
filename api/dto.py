from pydantic import BaseModel, Field

class ApiGroupDTO(BaseModel):
    id: int
    name: str


class ApiRegionDTO(BaseModel):
    id: int
    name: str
    time_zone_id: str = Field(alias='timeZoneId')

class ApiUserDTO(BaseModel):
    id: int
    telegram_id: int | None = Field(alias='telegramId')
    group_id: int = Field(alias='groupId')
    region_id: int = Field(alias='regionId')
    is_admin: bool = Field(alias='isAdmin')

class LessonDTO(BaseModel):
    pair_number: int = Field(alias='pairNumber')
    pair_start_time: str = Field(alias='pairStartTime')
    pair_end_time: str = Field(alias='pairEndTime')
    subject_name: str | None = Field(None, alias='subjectName')
    subject_short_name: str | None = Field(None, alias='subjectShortName')
    subject_abbreviation: str | None = Field(None, alias='subjectAbbreviation')
    subject_type_abbreviation: str = Field(alias='subjectTypeAbbreviation')
    teacher_full_name: str = Field(alias='teacherFullName')
    lesson_url: str | None = Field(None, alias='lessonUrl')

class ScheduleOverrideInfoDTO(BaseModel):
    substituted_day_name: str = Field(alias='substitutedDayName')
    description: str | None = Field(None, alias='description')

class DailyScheduleDTO(BaseModel):
    date: str
    day_of_week_name: str = Field(alias='dayOfWeekName')
    day_of_week_abbreviation: str = Field(alias='dayOfWeekAbbreviation')
    week_number: int = Field(alias='weekNumber')
    is_even_week: bool = Field(alias='isEvenWeek')
    override_info: ScheduleOverrideInfoDTO | None = Field(None, alias='overrideInfo')
    group_name: str = Field(alias='groupName')
    lessons: list[LessonDTO]

class ApiTeacherInfoDTO(BaseModel):
    info_type_id: int = Field(alias='infoTypeId')
    info_type_name: str = Field(alias='infoTypeName')
    value: str

class ApiTeacherDTO(BaseModel):
    id: int
    first_name: str = Field(alias='firstName')
    last_name: str = Field(alias='lastName')
    middle_name: str | None = Field(None, alias='middleName')
    full_name: str = Field(alias='fullName')
    infos: list[ApiTeacherInfoDTO] = []

class ApiCreateUserDTO(BaseModel):
    telegram_id: int = Field(alias='telegramId')
    username: str | None = Field(None, alias='username')
    group_id: int = Field(alias='groupId')
    region_id: int = Field(alias='regionId')
    is_admin: bool = Field(False, alias='isAdmin')

    class Config:
        populate_by_name = True

class ApiGroupedSubjectDTO(BaseModel):
    name: str
    abbreviation: str

class ApiSubjectTypeDTO(BaseModel):
    id: int
    name: str
    abbreviation: str

class ApiSubjectInfoDTO(BaseModel):
    info_type_id: int = Field(alias='infoTypeId')
    info_type_name: str = Field(alias='infoTypeName')
    value: str
    description: str | None = Field(None, alias='description')

class ApiSubjectVariantDTO(BaseModel):
    id: int
    subject_type: ApiSubjectTypeDTO = Field(alias='subjectType')
    teachers: list[ApiTeacherDTO] = [] 
    infos: list[ApiSubjectInfoDTO] = []

class ApiGroupedSubjectDetailsDTO(BaseModel):
    name: str
    short_name: str = Field(alias='shortName')
    abbreviation: str
    variants: list[ApiSubjectVariantDTO] = []

class ApiSemesterDTO(BaseModel):
    id: int
    start_date: str = Field(alias='startDate')
    end_date: str = Field(alias='endDate')