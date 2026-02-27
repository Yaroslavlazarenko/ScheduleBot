# bot/middlewares/di.py
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from application.bot_services import BotServices

class DiMiddleware(BaseMiddleware):
    def __init__(self, services: BotServices):
        super().__init__()
        self.services = services

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data['services'] = self.services
        return await handler(event, data)