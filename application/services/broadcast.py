import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from api.dto import PendingBroadcastDTO
from api.exceptions import ApiBadRequestError, ApiClientError, ResourceNotFoundError
from api.gateways.broadcast_gateway import BroadcastGateway
from config import settings

logger = logging.getLogger(__name__)

class BroadcastService:
    def __init__(self, gateway: BroadcastGateway):
        self._gateway = gateway

    async def create_broadcast(self, message_text: str, scheduled_at: str | None = None) -> str:
        """Створює завдання на розсилку через API та повертає повідомлення для адміна."""
        try:
            await self._gateway.create_broadcast(
                message_text=message_text,
                admin_api_key=settings.admin_api_key,
                scheduled_at=scheduled_at
            )
            
            if scheduled_at:
                return f"✅ Розсилку успішно заплановано на {scheduled_at} (UTC)!"
            else:
                return "✅ Завдання на негайну розсилку успішно створено!"

        except ApiBadRequestError as e:
            return f"❌ Помилка валідації: {e.message}"
        except ApiClientError as e:
            if e.status_code == 401:
                return "❌ Помилка авторизації: Невірний ключ доступу до API. Перевірте налаштування."
            return f"❌ Сталася непередбачена помилка API ({e.status_code}) при створенні розсилки."

    async def send_pending_broadcast(self, bot: Bot) -> str:
        """
        Отримує одне завдання на розсилку з API, виконує його та повертає звіт.
        """
        try:
            pending_data = await self._gateway.get_pending_broadcast(admin_api_key=settings.admin_api_key)
            if not pending_data:
                return "ℹ️ Немає активних розсилок для відправки."
                
            broadcast = PendingBroadcastDTO.model_validate(pending_data)
            
        except ResourceNotFoundError:
            return "ℹ️ Немає активних розсилок для відправки."
        except ApiClientError as e:
            return f"❌ Помилка отримання завдання на розсилку: {e.message}"

        success_count = 0
        failure_count = 0

        for user in broadcast.users:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=broadcast.message_text,
                    parse_mode="HTML"
                )
                success_count += 1
            except TelegramBadRequest as e:
                logger.warning("Failed to send broadcast to user %d: %s", user.telegram_id, e)
                failure_count += 1
            except Exception:
                logger.exception("Unexpected error sending to user %d", user.telegram_id)
                failure_count += 1
            
            await asyncio.sleep(0.1)

        try:
            await self._gateway.mark_broadcast_as_sent(
                broadcast_id=broadcast.id,
                admin_api_key=settings.admin_api_key
            )
            logger.info("Broadcast #%d marked as sent.", broadcast.id)
        except ApiClientError as e:
            logger.error("CRITICAL: Failed to mark broadcast #%d as sent: %s", broadcast.id, e)
            return "🔴 КРИТИЧНА ПОМИЛКА: розсилку було надіслано, але не вдалося позначити її як виконану. Можливі повторні відправки!"

        return (
            f"✅ Розсилку завершено!\n\n"
            f"🟢 Надіслано успішно: {success_count}\n"
            f"🔴 Не вдалося надіслати: {failure_count}"
        )