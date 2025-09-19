import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config

import telegram.handlers.text as text_handler

async def main():
    config = Config()
    
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 1. Создаем хранилище
    storage = MemoryStorage()

    
    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=None))

    dispatcher = Dispatcher(
        storage=storage
    )

    dispatcher.include_router(text_handler.router)

    logging.info("Starting bot...")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")