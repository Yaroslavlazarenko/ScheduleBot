import logging
import uuid # <-- Додано
from datetime import date, timedelta, datetime, time 
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

    def get_group_events_data(self, group_id: int) -> list:
        """Збирає список унікальних пар для Google Calendar API як події, що повторюються (RRULE)."""
        group = self.db.get_group(group_id)
        if not group:
            return[]

        # 1. Беремо старт семестру
        start_date_str = self.db.data.get("metadata", {}).get("semester_start", "2024-09-01")
        try:
            start_date = date.fromisoformat(start_date_str)
        except ValueError:
            start_date = date.today()
            
        group_entries =[e for e in self.db.data.get("schedule_entries", []) if e.get("group_id") == group_id]
        global_total_weeks = self.db.data.get("metadata", {}).get("total_weeks", 20)
        
        events =[]

        for entry in group_entries:
            day_of_week = entry.get("day_of_week")
            parity = entry.get("week_parity", "всі")
            week_start = entry.get("week_start", 1)
            week_end = entry.get("week_end", global_total_weeks)
            
            if week_end == 99:
                week_end = global_total_weeks

            # 2. Шукаємо найпершу дату, коли відбудеться ця конкретна пара
            search_start_date = start_date + timedelta(days=(week_start - 1) * 7)
            first_occurrence_date = None
            
            # Перевіряємо наступні 14 днів, щоб знайти потрібний день тижня та правильну парність
            for i in range(14):
                candidate = search_start_date + timedelta(days=i)
                if candidate.isoweekday() == day_of_week:
                    _, cand_parity = self._get_week_parity(candidate)
                    if parity == "всі" or cand_parity == parity:
                        first_occurrence_date = candidate
                        break
                        
            if not first_occurrence_date:
                continue # Якщо не знайшли (що малоймовірно), пропускаємо

            # 3. Формуємо правило повторення (RRULE)
            # Визначаємо крайній термін - до кінця тижня `week_end`
            end_date_limit = start_date + timedelta(days=week_end * 7)
            until_str = end_date_limit.strftime("%Y%m%dT235959Z") # Формат часу UTC для Google
            
            if parity == "всі":
                rrule = f"RRULE:FREQ=WEEKLY;UNTIL={until_str}"
            else:
                # Для парних/непарних тижнів повторюємо пару кожні 2 тижні
                rrule = f"RRULE:FREQ=WEEKLY;INTERVAL=2;UNTIL={until_str}"

            # 4. Витягуємо дані про предмет, викладача і час
            subject = next((s for s in self.db.data.get("subjects", []) if s["subject_id"] == entry["subject_id"]), None)
            teacher = next((t for t in self.db.data.get("teachers", []) if t["teacher_id"] == entry["teacher_id"]), None)
            period = next((p for p in self.db.data.get("periods", []) if p["period_number"] == entry["period_number"]), None)
            
            if not subject or not period:
                continue
                
            try:
                start_h, start_m = map(int, period["start_time"].split(":"))
                end_h, end_m = map(int, period["end_time"].split(":"))
            except ValueError:
                continue 
            
            start_dt = datetime.combine(first_occurrence_date, time(start_h, start_m))
            end_dt = datetime.combine(first_occurrence_date, time(end_h, end_m))
            
            summary = f"{subject['full_name']} ({entry['class_type']})"
            
            # --- НОВЕ: Формуємо розширений опис з усіма контактами ---
            desc_lines =[]
            if teacher: 
                desc_lines.append(f"👨‍🏫 <b>Викладач:</b> {teacher['title']} {teacher['name']}")
                if teacher.get('contacts'):
                    desc_lines.append(f"📞 <b>Контакти:</b> {teacher['contacts']}")
                if teacher.get('photo_url'):
                    desc_lines.append(f"🖼 <b>Фото / Профіль:</b> <a href='{teacher['photo_url']}'>Відкрити</a>")
                    
            desc_lines.append("") # Порожній рядок для відступу
            # --------------------------------------------------------

            meeting_url = entry.get('meeting_url')
            if meeting_url: 
                desc_lines.append(f"🔗 <b>Посилання на пару:</b> <a href='{meeting_url}'>{meeting_url}</a>")
                
            description = "<br>".join(desc_lines)

            # --- НОВЕ: Визначаємо колір (10 - зелений Basil, 9 - синій Blueberry) ---
            event_color = "10" if entry['class_type'].lower() == "лекція" else "9"

            events.append({
                "summary": summary,
                "description": description,
                "start_dt": start_dt,
                "end_dt": end_dt,
                "recurrence": [rrule],
                "colorId": event_color # <-- Передаємо колір
            })
            
        return events
    
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