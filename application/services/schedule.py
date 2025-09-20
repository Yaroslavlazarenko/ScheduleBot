from datetime import date, time
from api import DailyScheduleDTO

from api.gateways import ScheduleGateway

from .user import UserService
from .region import RegionService

MONTHS_UA = {
    1: "Січня", 2: "Лютого", 3: "Березня", 4: "Квітня",
    5: "Травня", 6: "Червня", 7: "Липня", 8: "Серпня",
    9: "Вересня", 10: "Жовтня", 11: "Листопада", 12: "Грудня"
}

def get_seasonal_emoji(current_date: date) -> str:
    """Повертає емодзі відповідно до пори року."""
    month = current_date.month
    if month in [12, 1, 2]:
        return "❄️"  # Зима
    elif month in [3, 4, 5]:
        return "🌷"  # Весна
    elif month in [6, 7, 8]:
        return "☀️"  # Літо
    else:  # 9, 10, 11
        return "🍁"  # Осінь


class ScheduleService:
    def __init__(
        self,
        schedule_gateway: ScheduleGateway,
        user_service: UserService,
        region_service: RegionService
    ):
        self._schedule_gateway = schedule_gateway
        self._user_service = user_service
        self._region_service = region_service

    async def get_schedule_for_day(self, telegram_id: int, schedule_date: date) -> DailyScheduleDTO:
        """Отримує розклад для користувача на заданий день, використовуючи новий ендпоінт."""
        user = await self._user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Користувача не знайдено. Будь ласка, зареєструйтесь: /start")
        
        regions = await self._region_service.get_all_regions()
        user_region = next((r for r in regions if r.id == user.region_id), None)
        
        if not user_region:
            raise ValueError(f"Не вдалося знайти регіон з ID={user.region_id} для користувача.")

        time_zone_id = await self._region_service.get_timezone_by_id(user.region_id)
        if not time_zone_id:
            raise ValueError(f"Не вдалося знайти часовий пояс для регіону з ID={user.region_id}.")
                
        date_str = schedule_date.isoformat()
        
        schedule_data = await self._schedule_gateway.get_daily_schedule_for_group(
            group_id=user.group_id,
            time_zone_id=user_region.time_zone_id,
            date=date_str
        )
        
        return DailyScheduleDTO.model_validate(schedule_data)

    def format_schedule_message(self, schedule: DailyScheduleDTO) -> str:
        """Форматує об'єкт розкладу у повідомлення для користувача з урахуванням "вікон"."""
        schedule_date = date.fromisoformat(schedule.date)
        
        seasonal_emoji = get_seasonal_emoji(schedule_date)
        day = schedule_date.day
        month_name = MONTHS_UA.get(schedule_date.month, "")
        week_type = "парний" if schedule.is_even_week else "непарний"
        
        header1 = f"{seasonal_emoji} {schedule.day_of_week_name.capitalize()}. {day:02} {month_name}"
        header2 = f"{schedule.group_name} Тиждень {schedule.week_number} ({week_type})"
        parts = [header1, header2]
        
        if schedule.override_info:
            parts.append(f"❗️ <b>Заміна:</b> {schedule.override_info.substituted_day_name}")
            if schedule.override_info.description:
                parts.append(f"<i>{schedule.override_info.description}</i>")

        parts.append("━━━━━━━━━━━━━━━━━━")

        if not schedule.lessons:
            parts.append("🎉 Пар немає, можна відпочити!")
        else:
            # Створюємо словник для швидкого доступу до пари за її номером
            lessons_by_number = {lesson.pair_number: lesson for lesson in schedule.lessons}
            # Знаходимо максимальний номер пари на цей день
            max_pair = max(lessons_by_number.keys())

            # Ітеруємо від 1-ї до останньої пари, щоб показати "вікна"
            for pair_num in range(1, max_pair + 1):
                lesson = lessons_by_number.get(pair_num)
                
                if lesson:
                    # Якщо пара існує, форматуємо її
                    start_time = time.fromisoformat(lesson.pair_start_time).strftime('%-H:%M')
                    end_time = time.fromisoformat(lesson.pair_end_time).strftime('%-H:%M')
                    
                    lesson_name = lesson.subject_name
                    if lesson.lesson_url:
                        lesson_name = f"<a href='{lesson.lesson_url}'>{lesson_name}</a>"

                    lesson_line = (
                        f"{lesson.pair_number}. {lesson_name} "
                        f"({lesson.subject_type_abbreviation}) "
                        f"({start_time}-{end_time}) "
                        f"{lesson.teacher_full_name}"
                    )
                    parts.append(lesson_line)
                else:
                    # Якщо пари немає, показуємо "вікно"
                    parts.append(f"{pair_num}. 😴 Вікно")

        return "\n".join(parts)