import logging
from datetime import date, timedelta
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