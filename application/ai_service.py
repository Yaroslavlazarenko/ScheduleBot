import json
import logging
from datetime import datetime, date
from openai import AsyncOpenAI

from application.bot_services import BotServices, DAYS_UA
from config import settings

logger = logging.getLogger(__name__)

# Глобальний словник для зберігання історії в пам'яті (in-memory)
USER_HISTORY = {}

class AIService:
    def __init__(self, services: BotServices):
        self.services = services
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url
        )
        self.model = settings.model_name
        self.max_history_messages = 8

    async def process_user_message(self, telegram_id: int, text: str) -> tuple[str, dict | None]:
        user = self.services.get_user(telegram_id)
        if not user:
            return "Будь ласка, зареєструйтесь за допомогою команди /start перед спілкуванням.", None

        group_id = user["group_id"]
        group = self.services.db.get_group(group_id)
        group_name = group["name"] if group else "Невідомо"

        # Формуємо контекст
        now = datetime.now()
        current_datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
        current_day_ua = DAYS_UA.get(now.isoweekday(), "")

        # Клонуємо базу і видаляємо приватні дані користувачів
        db_copy = dict(self.services.db.data)
        db_copy.pop("users", None) 
        db_json_str = json.dumps(db_copy, ensure_ascii=False)

        system_prompt = f"""Ти - корисний AI-асистент для студентів.
Поточна дата та час: {current_datetime_str} ({current_day_ua}).
Студент навчається в групі: {group_name} (ID: {group_id}).

Ось база даних університету у форматі JSON (предмети, викладачі, розклад):
{db_json_str}

ІНСТРУКЦІЇ ФОРМАТУВАННЯ ТЕКСТУ (ДУЖЕ ВАЖЛИВО!):
1. Telegram підтримує ТІЛЬКИ ці HTML-теги. Дозволено використовувати ТІЛЬКИ їх:
   - <b>жирний текст</b>
   - <i>курсив</i>
   - <u>підкреслення</u>
   - <s>закреслений текст</s>
   - <code>код або моноширинний текст</code>
   - <a href="URL">текст посилання</a>
2. ЗАБОРОНЕНІ ТЕГИ:
   - КАТЕГОРИЧНО ЗАБОРОНЕНО: <br>, <br/>, </br>. Для нового рядка просто роби звичайний перенос (Enter / \n).
   - КАТЕГОРИЧНО ЗАБОРОНЕНО: <p>, </p>, <div>, <span>, <h1>, <h2>, <h3>, <ul>, <ol>, <li>.
3. ЗАБОРОНЕНИЙ MARKDOWN:
   - Не використовуй **жирний** чи *курсив*. Замість цього використовуй <b> і <i>.

ІНСТРУКЦІЯ ЩОДО РОЗКЛАДУ:
- Використовуй tool `get_schedule`, щоб отримати розклад на конкретний день.
- ВАЖЛИВО: Якщо ти викликаєш tool `get_schedule`, бот АВТОМАТИЧНО надішле користувачу красиве інтерактивне меню з розкладом (з кнопками).
- ТОМУ у своїй текстовій відповіді НЕ ПЕРЕРАХОВУЙ предмети з розкладу! Просто скажи щось на кшталт "Ось твій розклад на [дата]:" або побажай продуктивного дня.

Відповідай українською мовою, привітно і чітко."""

        if telegram_id not in USER_HISTORY:
            USER_HISTORY[telegram_id] = []

        messages =[{"role": "system", "content": system_prompt}]
        messages.extend(USER_HISTORY[telegram_id])
        messages.append({"role": "user", "content": text})

        tools =[{
            "type": "function",
            "function": {
                "name": "get_schedule",
                "description": "Повертає готовий розклад пар для користувача на певну дату.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_date": {
                            "type": "string",
                            "description": "Дата у форматі YYYY-MM-DD (наприклад: 2026-03-07)"
                        }
                    },
                    "required": ["target_date"]
                }
            }
        }]

        ui_action = None 

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
            response_message = response.choices[0].message
            raw_content = None

            if response_message.tool_calls:
                messages.append(response_message)
                
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "get_schedule":
                        args = json.loads(tool_call.function.arguments)
                        target_date_str = args.get("target_date", now.strftime("%Y-%m-%d"))
                        
                        try:
                            target_d = date.fromisoformat(target_date_str)
                            schedule_text = self.services.format_daily_schedule_by_group(group_id, target_d)
                            ui_action = {"type": "schedule", "date": target_d}
                        except Exception as e:
                            schedule_text = f"Помилка формату дати: {e}"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call.function.name,
                            "content": schedule_text
                        })

                second_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                raw_content = second_response.choices[0].message.content
            else:
                raw_content = response_message.content

            # === ВИПРАВЛЕННЯ: Гарантовано перетворюємо відповідь (raw_content) на рядок ===
            if isinstance(raw_content, list):
                parts =[]
                for p in raw_content:
                    if hasattr(p, 'text'):
                        parts.append(p.text)
                    elif isinstance(p, dict) and 'text' in p:
                        parts.append(p['text'])
                    else:
                        parts.append(str(p))
                final_answer = "".join(parts)
            elif raw_content is None:
                final_answer = ""
            else:
                final_answer = str(raw_content)
            # ==============================================================================

            USER_HISTORY[telegram_id].append({"role": "user", "content": text})
            USER_HISTORY[telegram_id].append({"role": "assistant", "content": final_answer})
            USER_HISTORY[telegram_id] = USER_HISTORY[telegram_id][-self.max_history_messages:]

            return final_answer, ui_action

        except Exception as e:
            logger.error(f"Помилка AI: {e}")
            return "Вибачте, сталася помилка при зверненні до нейромережі. Спробуйте пізніше.", None