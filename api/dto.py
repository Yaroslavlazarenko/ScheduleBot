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
    subject_name: str = Field(alias='subjectName')
    subject_short_name: str = Field(alias='subjectShortName')
    subject_abbreviation: str = Field(alias='subjectAbbreviation')
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
    lessons: list[LessonDTO]

class ApiCreateUserDTO(BaseModel):
    telegram_id: int = Field(alias='telegramId')
    username: str | None = Field(None, alias='username')
    group_id: int = Field(alias='groupId')
    region_id: int = Field(alias='regionId')
    is_admin: bool = Field(False, alias='isAdmin')

    class Config:
        populate_by_name = True