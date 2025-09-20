import logging
from datetime import date, timedelta

from aiogram import F, Router, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LinkPreviewOptions, Message, CallbackQuery

from application.services import ScheduleService
from bot.keyboards import create_schedule_navigation_keyboard, ScheduleCallbackFactory
from api.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)
schedule_router = Router(name="schedule_router")

@schedule_router.message(F.text == "🗓 Отримати розклад")
async def handle_get_schedule(message: Message, schedule_service: ScheduleService):
    """Обробляє запит на отримання розкладу на поточний день."""
    if not message.from_user:
        return
    
    today = date.today()
    await send_schedule_for_date(message, schedule_service, message.from_user.id, today)

@schedule_router.callback_query(ScheduleCallbackFactory.filter())
async def handle_schedule_navigation(
    query: CallbackQuery,
    callback_data: ScheduleCallbackFactory,
    schedule_service: ScheduleService,
    bot: Bot
):
    """Обробляє навігацію по днях розкладу для звичайних та інлайн-повідомлень."""

    current_date = date.fromisoformat(callback_data.current_date)
    
    if callback_data.action == "next":
        target_date = current_date + timedelta(days=1)
    elif callback_data.action == "prev":
        target_date = current_date - timedelta(days=1)
    else:
        await query.answer("Невідома дія.")
        return

    if isinstance(query.message, Message):
        await edit_schedule_for_date(
            query.message,
            schedule_service,
            callback_data.original_user_id,
            target_date
        )
    elif query.inline_message_id:
        await edit_inline_schedule_for_date(
            bot,
            query.inline_message_id,
            schedule_service,
            callback_data.original_user_id,
            target_date
        )
    else:
        await query.answer("Помилка: неможливо оновити це повідомлення.", show_alert=True)
        logger.warning(
            "Attempted to navigate schedule on a message with no context (message is None and inline_message_id is None)"
        )

    await query.answer()


async def send_schedule_for_date(
    message: Message,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date
):
    """Відправляє нове повідомлення з розкладом."""
    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id, target_date)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        keyboard = create_schedule_navigation_keyboard(target_date, original_user_id=telegram_id)
        await message.answer(
            response_text, 
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except (ValueError, ResourceNotFoundError) as e:
        await message.answer(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    except Exception:
        logger.exception("Failed to send schedule for date %s", target_date)
        await message.answer("Сталася непередбачена помилка при отриманні розкладу.")


async def edit_schedule_for_date(
    message: types.Message,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date
):
    """Редагує існуюче повідомлення з розкладом."""
    if not isinstance(message, Message):
        return

    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id, target_date)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        keyboard = create_schedule_navigation_keyboard(target_date, original_user_id=telegram_id)
        await message.edit_text(
            response_text, 
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        pass
    except (ValueError, ResourceNotFoundError) as e:
        await message.edit_text(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    except Exception:
        logger.exception("Failed to edit schedule for date %s", target_date)
        await message.edit_text("Сталася непередбачена помилка при оновленні розкладу.")

async def edit_inline_schedule_for_date(
    bot: Bot,
    inline_message_id: str,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date
):
    """Редагує існуюче інлайн-повідомлення з розкладом."""
    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id, target_date)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        keyboard = create_schedule_navigation_keyboard(target_date, original_user_id=telegram_id)
        
        await bot.edit_message_text(
            text=response_text,
            inline_message_id=inline_message_id,
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        pass
    except (ValueError, ResourceNotFoundError) as e:
        logger.warning("Failed to edit inline schedule for user %d: %s", telegram_id, e)
    except Exception:
        logger.exception("Failed to edit inline schedule for date %s", target_date)