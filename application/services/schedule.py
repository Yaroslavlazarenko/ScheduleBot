from datetime import date, time
from api import DailyScheduleDTO
from api.gateways import UserGateway
from .user import UserService

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
    def __init__(self, user_gateway: UserGateway, user_service: UserService):
        self._user_gateway = user_gateway
        self._user_service = user_service

    async def get_schedule_for_day(self, telegram_id: int, schedule_date: date) -> DailyScheduleDTO:
        """Отримує розклад для користувача на заданий день."""
        user = await self._user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise ValueError("Користувача не знайдено. Будь ласка, зареєструйтесь: /start")
        
        date_str = schedule_date.isoformat()
        schedule_data = await self._user_gateway.get_schedule_for_user(user.id, date_str)
        
        return DailyScheduleDTO.model_validate(schedule_data)

    def format_schedule_message(self, schedule: DailyScheduleDTO) -> str:
        """Форматує об'єкт розкладу у повідомлення для користувача."""
        schedule_date = date.fromisoformat(schedule.date)
        
        seasonal_emoji = get_seasonal_emoji(schedule_date)
        
        day = schedule_date.day
        month_name = MONTHS_UA.get(schedule_date.month, "")

        week_type_full = "парний" if schedule.is_even_week else "непарний"

        header_line1 = f"{seasonal_emoji} {schedule.day_of_week_name.capitalize()} {day:02} {month_name}"
        header_line2 = f"Тиждень {schedule.week_number} ({week_type_full})"
        
        parts = [header_line1, header_line2]
        
        if schedule.override_info:
            parts.append(f"❗️ <b>Заміна:</b> {schedule.override_info.substituted_day_name}")
            if schedule.override_info.description:
                parts.append(f"<i>{schedule.override_info.description}</i>")

        parts.append("━━━━━━━━━━━━━━━━━━")

        if not schedule.lessons:
            parts.append("🎉 Пар немає, можна відпочити!")
        else:
            for lesson in sorted(schedule.lessons, key=lambda l: l.pair_number):
                start_time = time.fromisoformat(lesson.pair_start_time).strftime('%-H:%M')
                end_time = time.fromisoformat(lesson.pair_end_time).strftime('%-H:%M')
                
                lesson_name = lesson.subject_name
                if lesson.lesson_url:
                    lesson_name = f"<a href='{lesson.lesson_url}'>{lesson_name}</a>"

                teacher_name = lesson.teacher_full_name
                lesson_line = (
                    f"{lesson.pair_number}. {lesson_name} "
                    f"({lesson.subject_type_abbreviation}) "
                    f"({start_time}-{end_time})"
                    f"\n👤 {teacher_name}"
                )
                parts.append(lesson_line)

        return "\n".join(parts)