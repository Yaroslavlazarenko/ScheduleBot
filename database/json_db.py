import json
import aiofiles
import asyncio
from typing import Dict, Any

class JsonDatabase:
    def __init__(self, file_path: str = "db.json"):
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def load(self):
        async with self._lock:
            try:
                async with aiofiles.open(self.file_path, mode='r', encoding='utf-8') as f:
                    content = await f.read()
                    self.data = json.loads(content)
            except FileNotFoundError:
                raise RuntimeError(f"Database file {self.file_path} not found!")

    async def save(self):
        async with self._lock:
            async with aiofiles.open(self.file_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(self.data, indent=2, ensure_ascii=False))

    def get_user(self, telegram_id: int) -> dict | None:
        return next((u for u in self.data.get("users", []) if u["telegram_id"] == telegram_id), None)

    async def save_user(self, telegram_id: int, username: str, group_id: int, region_id: int, timezone: str, is_admin: bool = False):
        user = self.get_user(telegram_id)
        if user:
            user["group_id"] = group_id
            user["region_id"] = region_id
            user["timezone"] = timezone
        else:
            # БЕЗПЕКА: гарантуємо, що список users існує, перед тим як додавати
            self.data.setdefault("users", []).append({
                "telegram_id": telegram_id,
                "username": username,
                "group_id": group_id,
                "region_id": region_id,
                "is_admin": is_admin,
                "timezone": timezone
            })
        await self.save()

    def get_all_users(self):
        return self.data.get("users", [])

    def get_groups(self):
        return self.data.get("groups", [])

    def get_group(self, group_id: int):
        return next((g for g in self.data.get("groups", []) if g["group_id"] == group_id), None)

    def get_regions(self):
        return self.data.get("regions", [])

    def get_region(self, region_id: int):
        return next((r for r in self.data.get("regions", []) if r["region_id"] == region_id), None)

    def get_teachers(self):
        return self.data.get("teachers", [])

    def get_subjects(self):
        return self.data.get("subjects", [])

    def get_schedule(self, group_id: int, day_of_week: int, parity: str):
        entries = [e for e in self.data.get("schedule_entries", []) 
                   if e["group_id"] == group_id and e["day_of_week"] == day_of_week 
                   and e["week_parity"] in [parity, "всі"]]
        
        result = []
        for entry in entries:
            subject = next(s for s in self.data["subjects"] if s["subject_id"] == entry["subject_id"])
            teacher = next(t for t in self.data["teachers"] if t["teacher_id"] == entry["teacher_id"])
            period = next(p for p in self.data["periods"] if p["period_number"] == entry["period_number"])
            
            result.append({
                "period_number": period["period_number"],
                "start_time": period["start_time"],
                "end_time": period["end_time"],
                "subject_name": subject["full_name"],
                "subject_type": entry["class_type"],
                "teacher_name": f"{teacher['title']} {teacher['name']}",
                "meeting_url": entry["meeting_url"]
            })
        return sorted(result, key=lambda x: x["period_number"])
    
    async def update_static_data(self, new_data: dict):
        """Оновлює розклад та налаштування, але зберігає існуючих користувачів."""
        async with self._lock:
            # Зберігаємо старих юзерів
            users = self.data.get("users", [])
            
            # Замінюємо все інше новими даними
            self.data = new_data
            
            # Повертаємо юзерів на місце
            self.data["users"] = users
            
            # Зберігаємо у файл
            async with aiofiles.open(self.file_path, mode='w', encoding='utf-8') as f:
                await f.write(json.dumps(self.data, indent=2, ensure_ascii=False))