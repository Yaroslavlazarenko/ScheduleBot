import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Підключаємо наші нові локальні модулі
from database.json_db import JsonDatabase
from application.bot_services import BotServices
from bot.middlewares.di import DiMiddleware
from bot import handlers
from config import settings

async def main():
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Починаємо ініціалізацію бота...")

    # 1. Завантаження локальної бази даних
    db = JsonDatabase("db.json")
    try:
        await db.load()
        logger.info(f"Базу даних успішно завантажено. Користувачів: {len(db.get_all_users())}")
    except Exception as e:
        logger.critical(f"Помилка завантаження бази даних: {e}")
        return

    services = BotServices(db=db)

    # 2. Налаштування Telegram-бота
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)

    dispatcher.update.middleware(DiMiddleware(services=services))

    logger.info("Підключення роутерів...")
    dispatcher.include_router(handlers.common_router)
    dispatcher.include_router(handlers.user_router)
    dispatcher.include_router(handlers.schedule_router)
    dispatcher.include_router(handlers.inline_router)
    dispatcher.include_router(handlers.teacher_router)
    dispatcher.include_router(handlers.subject_router)
    dispatcher.include_router(handlers.settings_router)
    dispatcher.include_router(handlers.admin_router)
    
    # AI Роутер має бути останнім, щоб ловити довільний текст
    dispatcher.include_router(handlers.ai_router) 

    logger.info("Бот успішно запущений та готовий до роботи!")
    
    # Видаляємо вебхуки та запускаємо поллінг
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Роботу бота завершено.")