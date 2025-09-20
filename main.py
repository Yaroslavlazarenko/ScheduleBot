import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from api import ApiClient
from application.services import GroupService, RegionService, UserService
from bot import handlers
from bot.middlewares import DiMiddleware
from config import settings


async def main():
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # --- Composition Root ---
    logging.info("Creating dependencies...")
    api_client = ApiClient(base_url=settings.api_base_url, api_key=settings.api_key, use_ssl=False)
    group_service = GroupService(client=api_client)
    user_service = UserService(client=api_client)
    region_service = RegionService(client=api_client)

    # --- Bot Initialization ---
    storage = MemoryStorage()
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dispatcher = Dispatcher(storage=storage)

    # --- Middleware Registration ---
    dispatcher.update.middleware(
        DiMiddleware(
            user_service=user_service,
            group_service=group_service,
            region_service=region_service
        )
    )

    # --- Router Registration ---
    logging.info("Including routers...")
    dispatcher.include_router(handlers.common_router)
    dispatcher.include_router(handlers.user_router)

    # --- Bot Start ---
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting polling...")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")