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

    def _create_events_sync(self, group_name: str, events_list: list, existing_calendar_id: str | None = None) -> str | None:
        try:
            creds = service_account.Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
            service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
            
            calendar_id = existing_calendar_id
            
            # 1. Якщо календар вже існує, очищаємо його від старих пар
            if calendar_id:
                try:
                    page_token = None
                    while True:
                        events = service.events().list(calendarId=calendar_id, pageToken=page_token).execute()
                        for event in events.get('items',[]):
                            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                        page_token = events.get('nextPageToken')
                        if not page_token:
                            break
                except Exception as e:
                    logger.warning(f"Не вдалося очистити старий календар, створюємо новий: {e}")
                    calendar_id = None
            
            # 2. Якщо календаря не було, створюємо новий
            if not calendar_id:
                calendar = {'summary': f'🗓 Розклад: {group_name}', 'timeZone': 'Europe/Kyiv'}
                created_calendar = service.calendars().insert(body=calendar).execute()
                calendar_id = created_calendar['id']
                
                rule = {'scope': {'type': 'default'}, 'role': 'reader'}
                service.acl().insert(calendarId=calendar_id, body=rule).execute()

            # 3. Додаємо нові пари (оновлений розклад)
            for ev in events_list:
                event_body = {
                    'summary': ev['summary'],
                    'description': ev['description'],
                    'start': {'dateTime': ev['start_dt'].isoformat(), 'timeZone': 'Europe/Kyiv'},
                    'end': {'dateTime': ev['end_dt'].isoformat(), 'timeZone': 'Europe/Kyiv'}
                }
                
                # Додаємо посилання на зустріч
                if ev.get('location'):
                    event_body['location'] = ev['location']
                    
                # Додаємо правило повторення (Щотижня / Раз на 2 тижні)
                if ev.get('recurrence'):
                    event_body['recurrence'] = ev['recurrence']

                service.events().insert(calendarId=calendar_id, body=event_body).execute()
                time.sleep(0.2) # Безпечна затримка між запитами API
            
            return calendar_id
        except Exception as e:
            logger.error(f"Помилка Google Calendar API: {e}")
            return None

    async def create_calendar_for_group(self, group_name: str, events_list: list, existing_calendar_id: str | None = None) -> str | None:
        return await asyncio.to_thread(self._create_events_sync, group_name, events_list, existing_calendar_id)