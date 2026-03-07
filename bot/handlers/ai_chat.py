import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from application.bot_services import BotServices
from application.ai_service import AIService

logger = logging.getLogger(__name__)
ai_router = Router(name="ai_router")

@ai_router.message(F.text)
async def handle_ai_chat(message: Message, services: BotServices):
    """Обробляє всі текстові повідомлення, які не підпадають під інші хендлери, надсилаючи їх до ШІ."""
    if not message.from_user or not message.text:
        return

    # Показуємо статус "Друкує...", щоб юзер бачив, що бот обробляє запит
    await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    # Ініціалізуємо сервіс
    ai_service = AIService(services=services)
    
    # Отримуємо відповідь
    response_text = await ai_service.process_user_message(
        telegram_id=message.from_user.id,
        text=message.text
    )
    
    # Відправляємо результат
    try:
        await message.reply(response_text)
    except Exception as e:
        logger.error(f"Помилка відправки HTML від ШІ: {e}")
        # Якщо нейронка порушила HTML форматування, відправляємо як звичайний текст
        await message.reply(response_text, parse_mode=None)