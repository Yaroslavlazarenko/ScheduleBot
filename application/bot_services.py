import logging
import uuid # <-- Додано
from datetime import date, timedelta, datetime, timezone
from database.json_db import JsonDatabase

logger = logging.getLogger(__name__)

MONTHS_UA = {1: "Січня", 2: "Лютого", 3: "Березня", 4: "Квітня", 5: "Травня", 6: "Червня", 7: "Липня", 8: "Серпня", 9: "Вересня", 10: "Жовтня", 11: "Листопада", 12: "Грудня"}
DAYS_UA = {1: "Понеділок", 2: "Вівторок", 3: "Середа", 4: "Четвер", 5: "П'ятниця", 6: "Субота", 7: "Неділя"}

class BotServices:
    def __init__(self, db: JsonDatabase):
        self.db = db

    def _get_week_parity(self, target_date: date) -> tuple[int, str]:
        start_date_str = self.db.data.get("metadata", {}).get("semester_start", "2024-09-01")
        start_date = date.fromisoformat(start_date_str)
        if target_date < start_date:
            return 1, "непарні"
        days_diff = (target_date - start_date).days
        week_number = (days_diff // 7) + 1
        return week_number, "парні" if week_number % 2 == 0 else "непарні"

    def get_user(self, telegram_id: int) -> dict | None:
        return self.db.get_user(telegram_id)

    def get_all_groups(self) -> list[dict]:
        return self.db.get_groups()

    def get_all_regions(self) -> list[dict]:
        return self.db.get_regions()

    async def register_user(self, telegram_id: int, username: str, group_id: int, region_id: int) -> str:
        region = self.db.get_region(region_id)
        timezone = region["timezone"] if region else "Europe/Kyiv"
        await self.db.save_user(telegram_id, username, group_id, region_id, timezone, False)
        return "✅ Вас успішно зареєстровано!"

    async def change_user_group(self, telegram_id: int, group_id: int):
        user = self.get_user(telegram_id)
        if user:
            await self.db.save_user(telegram_id, user.get("username", ""), group_id, user.get("region_id", 1), user.get("timezone", "Europe/Kyiv"), user.get("is_admin", False))

    async def change_user_region(self, telegram_id: int, region_id: int):
        user = self.get_user(telegram_id)
        region = self.db.get_region(region_id)
        if user and region:
            await self.db.save_user(telegram_id, user.get("username", ""), user.get("group_id", 0), region_id, region["timezone"], user.get("is_admin", False))

    def generate_group_ics_calendar(self, group_id: int) -> bytes | None:
        """Генерує файл розкладу .ics для конкретної групи виключно на навчальні тижні з нагадуваннями."""
        group = self.db.get_group(group_id)
        if not group:
            return None

        # 1. Беремо початок семестру
        start_date_str = self.db.data.get("metadata", {}).get("semester_start", "2024-09-01")
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            start_date = date.today()
            
        # 2. Знаходимо всі пари цієї групи, щоб визначити, скільки тижнів триває їхнє навчання
        group_entries =[e for e in self.db.data.get("schedule_entries", []) if e.get("group_id") == group_id]
        
        # 3. Шукаємо максимальний тиждень (week_end). 
        max_week = 0
        for entry in group_entries:
            we = entry.get("week_end")
            if we and we != 99 and we > max_week:
                max_week = we
                
        # Якщо week_end не вказано або стоїть 99, намагаємось взяти загальну кількість тижнів
        if max_week == 0:
            max_week = self.db.data.get("metadata", {}).get("total_weeks", 20)
        
        # Кінцева дата = початок семестру + кількість навчальних тижнів
        end_date = start_date + timedelta(weeks=max_week)

        # Стандартні заголовки iCalendar
        cal_lines =[
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//ScheduleBot//UA",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:Розклад {group['name']}",
            "X-WR-TIMEZONE:Europe/Kyiv"
        ]

        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.isoweekday()
            
            # Пропускаємо вихідні дні для оптимізації
            if day_of_week in [6, 7]:
                current_date += timedelta(days=1)
                continue

            week_number, parity = self._get_week_parity(current_date)
            lessons = self.db.get_schedule(group_id, day_of_week, parity, week_number)
            
            for l in lessons:
                try:
                    start_h, start_m = map(int, l["start_time"].split(":"))
                    end_h, end_m = map(int, l["end_time"].split(":"))
                except (ValueError, KeyError):
                    continue # Пропускаємо пару з некоректним часом
                
                # Формат дати і часу для .ics: YYYYMMDDTHHMMSS
                dtstart = f"{current_date.strftime('%Y%m%d')}T{start_h:02d}{start_m:02d}00"
                dtend = f"{current_date.strftime('%Y%m%d')}T{end_h:02d}{end_m:02d}00"
                
                # ФІКС: Робимо UID детермінованим (постійним). Без uuid! 
                # Якщо розклад зміниться, календар оновить подію, а не створить дублікат.
                uid = f"lesson-{group_id}-{current_date.strftime('%Y%m%d')}T{start_h:02d}{start_m:02d}@schedulebot"
                dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                
                summary = f"{l['subject_name']} ({l['subject_type']})"
                
                desc_lines =[]
                if l.get('teacher_name'): 
                    desc_lines.append(f"Викладач: {l['teacher_name']}")
                if l.get('meeting_url'): 
                    desc_lines.append(f"Посилання: {l['meeting_url']}")
                
                description = "\\n".join(desc_lines)
                
                cal_lines.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{dtstamp}",
                    f"DTSTART;TZID=Europe/Kyiv:{dtstart}",
                    f"DTEND;TZID=Europe/Kyiv:{dtend}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:{description}",
                    # ФІКС: Більш жорстке вказання 10 хвилин для всіх календарних клієнтів
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{summary}",
                    "TRIGGER;RELATED=START:-PT10M",
                    "END:VALARM",
                    "END:VEVENT"
                ])
                
            current_date += timedelta(days=1)

        cal_lines.append("END:VCALENDAR")
        
        # З'єднуємо з правильним закінченням рядків (\r\n за стандартом RFC 5545)
        ics_content = "\r\n".join(cal_lines)
        return ics_content.encode('utf-8')
    
    # --- Нові базові методи генерації по ID групи ---
    def format_daily_schedule_by_group(self, group_id: int, target_date: date) -> str:
        group = self.db.get_group(group_id)
        if not group:
            return "❌ Групу не знайдено."

        day_of_week = target_date.isoweekday()
        week_number, parity = self._get_week_parity(target_date)
        divider = "═" * 20
        header = f"🗓 <b>{DAYS_UA.get(day_of_week)}, {target_date.day} {MONTHS_UA.get(target_date.month)}</b>\n👥 {group['name']} · Тиждень {week_number} ({parity})\n{divider}\n"

        if day_of_week == 5:
            return header + "📚 День курсового проєктування"
        
        if day_of_week in [6, 7]:
            return header + "🎉 Вихідний день! Пар немає."

        # ПЕРЕДАЄМО week_number СЮДИ
        lessons = self.db.get_schedule(group_id, day_of_week, parity, week_number)
        
        if not lessons:
            return header + "🎉 Пар немає, можна відпочити!"

        parts = [header]
        max_period = max(l["period_number"] for l in lessons)
        lessons_map = {l["period_number"]: l for l in lessons}

        for i in range(1, max_period + 1):
            if i in lessons_map:
                l = lessons_map[i]
                link = f"<a href='{l['meeting_url']}'>{l['subject_name']}</a>" if l.get("meeting_url") else l['subject_name']
                parts.append(f"{i}. {link} ({l['subject_type']}) ({l['start_time']}-{l['end_time']})\n    └ <i>{l['teacher_name']}</i>")
            else:
                parts.append(f"{i}. 😴 Вікно")
        return "\n".join(parts)

    def format_weekly_schedule_by_group(self, group_id: int, start_date: date) -> str:
        group = self.db.get_group(group_id)
        if not group:
            return "❌ Групу не знайдено."

        week_number, parity = self._get_week_parity(start_date)
        monday = start_date - timedelta(days=start_date.isoweekday() - 1)
        friday = monday + timedelta(days=4)
        divider = "═" * 20

        header = f"🗓 Розклад на тиждень ({monday.strftime('%d.%m')} - {friday.strftime('%d.%m')})\n👥 {group['name']} · Тиждень {week_number} ({parity})\n{divider}"
        parts = [header]

        for i in range(5): 
            current_day = monday + timedelta(days=i)
            day_of_week = current_day.isoweekday()
            parts.append(f"\n<b><u>{DAYS_UA.get(day_of_week)}, {current_day.day} {MONTHS_UA.get(current_day.month)}</u></b>")

            if day_of_week == 5:
                parts.append("  📚 <i>День курсового проєктування</i>")
                continue
            
            # ПЕРЕДАЄМО week_number СЮДИ
            lessons = self.db.get_schedule(group_id, day_of_week, parity, week_number)
            
            if not lessons:
                parts.append("  🎉 <i>Пар немає</i>")
                continue

            max_period = max(l["period_number"] for l in lessons)
            lessons_map = {l["period_number"]: l for l in lessons}

            for period in range(1, max_period + 1):
                if period in lessons_map:
                    l = lessons_map[period]
                    parts.append(f"  {period}. {l['subject_name']} ({l['subject_type']})")
                else:
                    parts.append(f"  {period}. 😴 Вікно")
        return "\n".join(parts)

    # --- Старі методи для сумісності з особистими повідомленнями ---
    def format_daily_schedule(self, telegram_id: int, target_date: date) -> str:
        user = self.get_user(telegram_id)
        if not user: raise ValueError("Користувача не знайдено в базі.")
        return self.format_daily_schedule_by_group(user["group_id"], target_date)

    def format_weekly_schedule(self, telegram_id: int, start_date: date) -> str:
        user = self.get_user(telegram_id)
        if not user: raise ValueError("Користувача не знайдено в базі.")
        return self.format_weekly_schedule_by_group(user["group_id"], start_date)