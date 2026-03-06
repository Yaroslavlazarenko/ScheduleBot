import asyncio
import logging
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleCalendarAPI:
    def __init__(self, creds_path="credentials.json"):
        self.creds_path = creds_path
        self.scopes = ['https://www.googleapis.com/auth/calendar']

    def _create_events_sync(self, group_name: str, events_list: list) -> str | None:
        try:
            # Авторизація через Service Account
            creds = service_account.Credentials.from_service_account_file(
                self.creds_path, scopes=self.scopes)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            
            # 1. Створюємо новий календар
            calendar = {
                'summary': f'🗓 Розклад: {group_name}',
                'timeZone': 'Europe/Kyiv'
            }
            created_calendar = service.calendars().insert(body=calendar).execute()
            calendar_id = created_calendar['id']
            
            # 2. Робимо календар публічним (щоб студенти могли зайти за посиланням)
            rule = {'scope': {'type': 'default'}, 'role': 'reader'}
            service.acl().insert(calendarId=calendar_id, body=rule).execute()

            # 3. Додаємо всі події по одній (з паузою, щоб Google не заблокував за спам запитами)
            for ev in events_list:
                event_body = {
                    'summary': ev['summary'],
                    'description': ev['description'],
                    'start': {'dateTime': ev['start_dt'].isoformat(), 'timeZone': 'Europe/Kyiv'},
                    'end': {'dateTime': ev['end_dt'].isoformat(), 'timeZone': 'Europe/Kyiv'},
                    'reminders': {
                        'useDefault': False, # Вимикаємо стандартні 30 хвилин
                        'overrides': [{'method': 'popup', 'minutes': 10}], # Жорстко ставимо 10 хвилин
                    },
                }
                service.events().insert(calendarId=calendar_id, body=event_body).execute()
                time.sleep(0.2) # Безпечна затримка між запитами API
            
            return calendar_id
        except Exception as e:
            logger.error(f"Помилка Google Calendar API: {e}")
            return None

    async def create_calendar_for_group(self, group_name: str, events_list: list) -> str | None:
        """Асинхронна обгортка для створення календаря."""
        return await asyncio.to_thread(self._create_events_sync, group_name, events_list)