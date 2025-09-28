    
from api.exceptions import ApiBadRequestError, ApiClientError
from api.gateways.broadcast_gateway import BroadcastGateway
from config import settings

class BroadcastService:
    def __init__(self, gateway: BroadcastGateway):
        self._gateway = gateway

    async def create_broadcast(
        self,
        message_text: str,
        scheduled_at: str | None = None
    ) -> str:
        """
        Створює розсилку через API та повертає повідомлення для адміна.
        """
        try:
            await self._gateway.create_broadcast(
                message_text=message_text,
                admin_api_key=settings.admin_api_key,
                scheduled_at=scheduled_at
            )
            
            if scheduled_at:
                response = (
                    f"✅ Розсилку успішно заплановано на {scheduled_at} (UTC)!\n\n"
                    "Вона буде надіслана при наступному запуску скрипта розсилки після вказаного часу."
                )
            else:
                response = (
                    "✅ Розсилку для негайної відправки успішно створено!\n\n"
                    "Вона буде надіслана при наступному запуску скрипта `scripts/broadcast.py`."
                )
            return response

        except ApiBadRequestError as e:
            return f"❌ Помилка валідації: {e.message}"
        except ApiClientError as e:
            if e.status_code == 401:
                return "❌ Помилка авторизації: Невірний ключ доступу до API. Перевірте налаштування."
            return f"❌ Сталася непередбачена помилка API ({e.status_code}) при створенні розсилки."

  