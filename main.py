import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from api import ApiClient
from api.gateways import (GroupGateway, RegionGateway, ScheduleGateway,
                          UserGateway, TeacherGateway, SubjectGateway,
                          SemesterGateway, BroadcastGateway)
from application.services import (GroupService, RegionService, ScheduleService,
                                  UserService, TeacherService, SubjectService,
                                  SemesterService, BroadcastService)
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

    api_client = ApiClient(base_url=settings.api_base_url, api_key=settings.api_key)

    user_gateway = UserGateway(client=api_client)
    group_gateway = GroupGateway(client=api_client)
    region_gateway = RegionGateway(client=api_client)
    schedule_gateway = ScheduleGateway(client=api_client)
    teacher_gateway = TeacherGateway(client=api_client)
    subject_gateway = SubjectGateway(client=api_client)
    semester_gateway = SemesterGateway(client=api_client)
    broadcast_gateway = BroadcastGateway(client=api_client)

    group_service = GroupService(gateway=group_gateway)
    user_service = UserService(gateway=user_gateway)
    region_service = RegionService(gateway=region_gateway)
    teacher_service = TeacherService(gateway=teacher_gateway)
    semester_service = SemesterService(gateway=semester_gateway)
    subject_service = SubjectService(gateway=subject_gateway, teacher_service=teacher_service)
    broadcast_service = BroadcastService(gateway=broadcast_gateway)

    schedule_service = ScheduleService(
        schedule_gateway=schedule_gateway,
        user_service=user_service,
        region_service=region_service
    )

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
            region_service=region_service,
            schedule_service=schedule_service,
            teacher_service=teacher_service,
            subject_service=subject_service,
            semester_service=semester_service,
            broadcast_service=broadcast_service
        )
    )

    # --- Router Registration ---
    logging.info("Including routers...")
    dispatcher.include_router(handlers.common_router)
    dispatcher.include_router(handlers.user_router)
    dispatcher.include_router(handlers.schedule_router)
    dispatcher.include_router(handlers.inline_router)
    dispatcher.include_router(handlers.teacher_router)
    dispatcher.include_router(handlers.settings_router)
    dispatcher.include_router(handlers.subject_router)
    dispatcher.include_router(handlers.admin_router)

    # --- Bot Start ---
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Starting polling...")
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")