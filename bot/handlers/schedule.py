import logging
from datetime import date, timedelta
from typing import Callable, Awaitable

from aiogram import F, Router, types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LinkPreviewOptions, Message, CallbackQuery

from application.services import ScheduleService, SemesterService
from bot.keyboards import (create_schedule_navigation_keyboard, ScheduleCallbackFactory, 
                           create_show_schedule_keyboard, create_weekly_schedule_navigation_keyboard) 
from api.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)
schedule_router = Router(name="schedule_router")

@schedule_router.message(F.text == "🗓 Отримати розклад")
async def handle_get_schedule(message: Message, schedule_service: ScheduleService, semester_service: SemesterService):
    """
    Обробляє запит на отримання розкладу на поточний день,
    відправляє розклад і видаляє повідомлення користувача.
    """
    if not message.from_user:
        return
    
    telegram_id = message.from_user.id
    
    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        
        current_schedule_date = date.fromisoformat(schedule_dto.date)

        semester = await semester_service.get_current_semester()
        semester_start = date.fromisoformat(semester.start_date.split('T')[0]) if semester else None
        semester_end = date.fromisoformat(semester.end_date.split('T')[0]) if semester else None

        keyboard = create_schedule_navigation_keyboard(
            current_schedule_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
        
        await message.answer(
            response_text, 
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except (ValueError, ResourceNotFoundError) as e:
        await message.answer(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    except Exception:
        logger.exception("Failed to send schedule for user %d", telegram_id)
        await message.answer("Сталася непередбачена помилка при отриманні розкладу.")
    finally:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            logger.warning("Could not delete user's schedule request message: %s", e)

@schedule_router.message(F.text == "🗓 Розклад на тиждень")
async def handle_get_weekly_schedule(message: Message, schedule_service: ScheduleService, semester_service: SemesterService):
    """
    Обробляє запит на отримання розкладу на поточний тиждень.
    """
    if not message.from_user:
        return
    
    telegram_id = message.from_user.id
    
    try:
        schedule_dto = await schedule_service.get_schedule_for_week(telegram_id)
        response_text = schedule_service.format_weekly_schedule_message(schedule_dto)
        
        current_schedule_date = date.fromisoformat(schedule_dto.week_start_date)

        semester = await semester_service.get_current_semester()
        semester_start = date.fromisoformat(semester.start_date.split('T')[0]) if semester else None
        semester_end = date.fromisoformat(semester.end_date.split('T')[0]) if semester else None

        keyboard = create_weekly_schedule_navigation_keyboard(
            current_schedule_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
        
        await message.answer(
            response_text, 
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except (ValueError, ResourceNotFoundError) as e:
        await message.answer(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    except Exception:
        logger.exception("Failed to send weekly schedule for user %d", telegram_id)
        await message.answer("Сталася непередбачена помилка при отриманні розкладу.")
    finally:
        try:
            await message.delete()
        except TelegramBadRequest as e:
            logger.warning("Could not delete user's weekly schedule request message: %s", e)


@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action == "close"))
async def handle_close_schedule(query: CallbackQuery, callback_data: ScheduleCallbackFactory, bot: Bot):
    """
    Обробляє натискання кнопки "Закрити".
    - Для звичайних повідомлень - видаляє їх.
    - Для інлайн-повідомлень - редагує, показуючи кнопку "Отримати розклад".
    """
    if isinstance(query.message, Message):
        try:
            await query.message.delete()
        except TelegramBadRequest as e:
            logger.warning("Could not delete schedule message: %s", e)
    elif query.inline_message_id:
        try:
            keyboard = create_show_schedule_keyboard(callback_data.original_user_id)
            await bot.edit_message_text(
                text="Розклад згорнуто",
                inline_message_id=query.inline_message_id,
                reply_markup=keyboard
            )
        except TelegramBadRequest as e:
            logger.warning("Could not edit inline message on close: %s", e)
    
    await query.answer()

@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action == "show"))
async def handle_show_schedule(
    query: CallbackQuery,
    callback_data: ScheduleCallbackFactory,
    schedule_service: ScheduleService,
    semester_service: SemesterService,
    bot: Bot
):
    """Обробляє натискання кнопки 'Отримати розклад' для інлайн-повідомлення."""
    if not query.inline_message_id:
        await query.answer("Ця дія доступна лише для інлайн-розкладу.", show_alert=True)
        return
        
    telegram_id = callback_data.original_user_id
    
    semester = await semester_service.get_current_semester()
    semester_start = date.fromisoformat(semester.start_date.split('T')[0]) if semester else None
    semester_end = date.fromisoformat(semester.end_date.split('T')[0]) if semester else None
    
    await edit_inline_schedule_for_date(
        bot,
        query.inline_message_id,
        schedule_service,
        telegram_id,
        None,
        semester_start,
        semester_end
    )
    await query.answer()

@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action.in_({"prev", "next", "prev_week", "next_week"})))
async def handle_schedule_navigation(
    query: CallbackQuery,
    callback_data: ScheduleCallbackFactory,
    schedule_service: ScheduleService,
    semester_service: SemesterService,
    bot: Bot
):
    """Обробляє навігацію по днях та тижнях розкладу для звичайних та інлайн-повідомлень."""
    semester = await semester_service.get_current_semester()
    if not semester:
        await query.answer("Не вдалося знайти активний семестр.", show_alert=True)
        return

    semester_start = date.fromisoformat(semester.start_date.split('T')[0])
    semester_end = date.fromisoformat(semester.end_date.split('T')[0])
    current_date = date.fromisoformat(callback_data.current_date)
    
    target_date: date
    edit_func_regular: Callable[..., Awaitable[None]]
    edit_func_inline: Callable[..., Awaitable[None]]

    if callback_data.action in ("next", "prev"):
        delta = timedelta(days=1) if callback_data.action == "next" else -timedelta(days=1)
        target_date = max(min(current_date + delta, semester_end), semester_start)
        edit_func_regular = edit_schedule_for_date
        edit_func_inline = edit_inline_schedule_for_date
    else:
        delta = timedelta(weeks=1) if callback_data.action == "next_week" else -timedelta(weeks=1)
        target_date = max(min(current_date + delta, semester_end), semester_start)
        edit_func_regular = edit_weekly_schedule_for_date
        edit_func_inline = edit_inline_weekly_schedule_for_date

    if isinstance(query.message, Message):
        await edit_func_regular(
            message=query.message,
            schedule_service=schedule_service,
            telegram_id=callback_data.original_user_id,
            target_date=target_date,
            semester_start=semester_start,
            semester_end=semester_end
        )
    elif query.inline_message_id:
        await edit_func_inline(
            bot=bot,
            inline_message_id=query.inline_message_id,
            schedule_service=schedule_service,
            telegram_id=callback_data.original_user_id,
            target_date=target_date,
            semester_start=semester_start,
            semester_end=semester_end
        )
    else:
        await query.answer("Помилка: неможливо оновити це повідомлення.", show_alert=True)
        logger.warning(
            "Attempted to navigate schedule on a message with no context"
        )

    await query.answer()

async def edit_schedule_for_date(
    message: types.Message,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date,
    semester_start: date | None,
    semester_end: date | None
):
    """Редагує існуюче повідомлення з денним розкладом."""
    if not isinstance(message, Message):
        return

    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id, target_date)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        keyboard = create_schedule_navigation_keyboard(
            target_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
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

async def edit_weekly_schedule_for_date(
    message: types.Message,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date,
    semester_start: date | None,
    semester_end: date | None
):
    """Редагує існуюче повідомлення з тижневим розкладом."""
    if not isinstance(message, Message):
        return

    try:
        schedule_dto = await schedule_service.get_schedule_for_week(telegram_id, target_date)
        response_text = schedule_service.format_weekly_schedule_message(schedule_dto)
        current_week_start_date = date.fromisoformat(schedule_dto.week_start_date)
        keyboard = create_weekly_schedule_navigation_keyboard(
            current_week_start_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
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
        logger.exception("Failed to edit weekly schedule for date %s", target_date)
        await message.edit_text("Сталася непередбачена помилка при оновленні розкладу.")

async def edit_inline_schedule_for_date(
    bot: Bot,
    inline_message_id: str,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date | None,
    semester_start: date | None,
    semester_end: date | None    
):
    """Редагує існуюче інлайн-повідомлення з денним розкладом."""
    try:
        schedule_dto = await schedule_service.get_schedule_for_day(telegram_id, target_date)
        response_text = schedule_service.format_schedule_message(schedule_dto)
        current_schedule_date = date.fromisoformat(schedule_dto.date)
        keyboard = create_schedule_navigation_keyboard(
            current_schedule_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
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

async def edit_inline_weekly_schedule_for_date(
    bot: Bot,
    inline_message_id: str,
    schedule_service: ScheduleService,
    telegram_id: int,
    target_date: date,
    semester_start: date | None,
    semester_end: date | None    
):
    """Редагує існуюче інлайн-повідомлення з тижневим розкладом."""
    try:
        schedule_dto = await schedule_service.get_schedule_for_week(telegram_id, target_date)
        response_text = schedule_service.format_weekly_schedule_message(schedule_dto)
        current_week_start_date = date.fromisoformat(schedule_dto.week_start_date)
        keyboard = create_weekly_schedule_navigation_keyboard(
            current_week_start_date, 
            original_user_id=telegram_id,
            semester_start=semester_start,
            semester_end=semester_end
        )
        await bot.edit_message_text(
            text=response_text,
            inline_message_id=inline_message_id,
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        pass
    except (ValueError, ResourceNotFoundError) as e:
        logger.warning("Failed to edit inline weekly schedule for user %d: %s", telegram_id, e)
    except Exception:
        logger.exception("Failed to edit inline weekly schedule for date %s", target_date)