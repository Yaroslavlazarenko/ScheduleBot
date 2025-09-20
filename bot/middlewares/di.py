from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from application.services import GroupService, RegionService, UserService, ScheduleService, TeacherService

class DiMiddleware(BaseMiddleware):
    def __init__(
        self, 
        user_service: UserService, 
        group_service: GroupService, 
        region_service: RegionService,
        schedule_service: ScheduleService,
        teacher_service: TeacherService
    ):
        super().__init__()
        self.user_service = user_service
        self.group_service = group_service
        self.region_service = region_service
        self.schedule_service = schedule_service
        self.teacher_service = teacher_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data['user_service'] = self.user_service
        data['group_service'] = self.group_service
        data['region_service'] = self.region_service
        data['schedule_service'] = self.schedule_service
        data['teacher_service'] = self.teacher_service
        return await handler(event, data)