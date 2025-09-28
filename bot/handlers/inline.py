import logging
from datetime import date
from uuid import uuid4

from aiogram import Bot, Router
from aiogram.types import (InlineQuery, InlineQueryResultArticle,
                           InputTextMessageContent, LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton)

from api.exceptions import ResourceNotFoundError
from application.services import ScheduleService, UserService, SemesterService
from bot.keyboards import create_schedule_navigation_keyboard, create_weekly_schedule_navigation_keyboard

logger = logging.getLogger(__name__)
inline_router = Router(name="inline_router")


@inline_router.inline_query()
async def handle_inline_query(
    query: InlineQuery,
    user_service: UserService,
    schedule_service: ScheduleService,
    semester_service: SemesterService,
    bot: Bot
):
    """
    Обробляє інлайн-запити.
    - Для зареєстрованих користувачів пропонує надіслати розклад на день та на тиждень.
    - Для незареєстрованих — пропонує перейти в бот для реєстрації.
    """
    results = []
    user_id = query.from_user.id
    user = await user_service.get_user_by_telegram_id(user_id)

    if user:
        try:
            schedule_dto = await schedule_service.get_schedule_for_day(user_id)
            response_text = schedule_service.format_schedule_message(schedule_dto)
            current_schedule_date = date.fromisoformat(schedule_dto.date)
            
            semester = await semester_service.get_current_semester()
            semester_start = date.fromisoformat(semester.start_date.split('T')[0]) if semester else None
            semester_end = date.fromisoformat(semester.end_date.split('T')[0]) if semester else None

            keyboard = create_schedule_navigation_keyboard(
                current_schedule_date, 
                original_user_id=user_id,
                semester_start=semester_start,
                semester_end=semester_end
            )

            schedule_result = InlineQueryResultArticle(
                id=str(uuid4()),
                title="🗓 Мій розклад на сьогодні",
                description="Натисніть, щоб надіслати розклад у цей чат.",
                input_message_content=InputTextMessageContent(
                    message_text=response_text,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                ),
                reply_markup=keyboard
            )
            results.append(schedule_result)

        except (ValueError, ResourceNotFoundError) as e:
            error_result = InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ Помилка отримання розкладу на день",
                description=str(e),
                input_message_content=InputTextMessageContent(message_text=f"❌ Помилка: {e}")
            )
            results.append(error_result)
        except Exception:
            logger.exception("Failed to create inline daily schedule for user %d", user_id)

        try:
            weekly_schedule_dto = await schedule_service.get_schedule_for_week(user_id)
            response_text = schedule_service.format_weekly_schedule_message(weekly_schedule_dto)
            current_schedule_date = date.fromisoformat(weekly_schedule_dto.week_start_date)
            
            semester = await semester_service.get_current_semester()
            semester_start = date.fromisoformat(semester.start_date.split('T')[0]) if semester else None
            semester_end = date.fromisoformat(semester.end_date.split('T')[0]) if semester else None

            keyboard = create_weekly_schedule_navigation_keyboard(
                current_schedule_date, 
                original_user_id=user_id,
                semester_start=semester_start,
                semester_end=semester_end
            )

            weekly_schedule_result = InlineQueryResultArticle(
                id=str(uuid4()),
                title="🗓 Мій розклад на тиждень",
                description="Натисніть, щоб надіслати розклад на весь тиждень.",
                input_message_content=InputTextMessageContent(
                    message_text=response_text,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                ),
                reply_markup=keyboard
            )
            results.append(weekly_schedule_result)
        except Exception:
            logger.exception("Failed to create inline weekly schedule for user %d", user_id)

    else:
        bot_user = await bot.get_me()

        registration_button = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="👉 Зареєструватися",
                    url=f"https://t.me/{bot_user.username}?start=register"
                )
            ]]
        )
        
        register_result = InlineQueryResultArticle(
            id=str(uuid4()),
            title="⚠️ Потрібна реєстрація",
            description="Щоб користуватися ботом, спершу потрібно зареєструватися.",
            input_message_content=InputTextMessageContent(
                message_text="Я бот для перегляду розкладу. Щоб почати, будь ласка, зареєструйтесь."
            ),
            reply_markup=registration_button
        )
        results.append(register_result)

    await query.answer(
        results=results,
        cache_time=10,
        is_personal=True
    )