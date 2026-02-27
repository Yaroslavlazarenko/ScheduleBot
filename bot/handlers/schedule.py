import logging
from datetime import date, timedelta
from aiogram import F, Router, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import LinkPreviewOptions, Message, CallbackQuery

from application.bot_services import BotServices
from bot.keyboards import ScheduleCallbackFactory, create_schedule_navigation_keyboard, create_weekly_schedule_navigation_keyboard, create_show_schedule_keyboard, create_show_weekly_schedule_keyboard

logger = logging.getLogger(__name__)
schedule_router = Router(name="schedule_router")

@schedule_router.message(F.text == "🗓 Отримати розклад")
async def handle_get_schedule(message: Message, services: BotServices):
    if not message.from_user: return
    try:
        user = services.get_user(message.from_user.id)
        if not user: raise ValueError("Користувача не знайдено.")
        
        target_date = date.today()
        group_id = user["group_id"]
        
        text = services.format_daily_schedule_by_group(group_id, target_date)
        keyboard = create_schedule_navigation_keyboard(target_date, group_id)
        
        await message.answer(text, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except ValueError as e:
        await message.answer(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    finally:
        try: await message.delete()
        except TelegramBadRequest: pass

@schedule_router.message(F.text == "🗓 Розклад на тиждень")
async def handle_get_weekly_schedule(message: Message, services: BotServices):
    if not message.from_user: return
    try:
        user = services.get_user(message.from_user.id)
        if not user: raise ValueError("Користувача не знайдено.")
        
        target_date = date.today()
        group_id = user["group_id"]
        
        text = services.format_weekly_schedule_by_group(group_id, target_date)
        keyboard = create_weekly_schedule_navigation_keyboard(target_date, group_id)
        
        await message.answer(text, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except ValueError as e:
        await message.answer(f"❌ Помилка: {e}\nСпробуйте почати з /start.")
    finally:
        try: await message.delete()
        except TelegramBadRequest: pass

@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action.in_({"prev", "next", "prev_week", "next_week"})))
async def handle_schedule_navigation(query: CallbackQuery, callback_data: ScheduleCallbackFactory, services: BotServices, bot: Bot):
    current_date = date.fromisoformat(callback_data.current_date)
    group_id = callback_data.group_id # Беремо ID групи прямо з кнопки!

    if callback_data.action == "prev": target_date = current_date - timedelta(days=1)
    elif callback_data.action == "next": target_date = current_date + timedelta(days=1)
    elif callback_data.action == "prev_week": target_date = current_date - timedelta(weeks=1)
    else: target_date = current_date + timedelta(weeks=1)

    try:
        if callback_data.schedule_type == "day":
            text = services.format_daily_schedule_by_group(group_id, target_date)
            keyboard = create_schedule_navigation_keyboard(target_date, group_id)
        else:
            text = services.format_weekly_schedule_by_group(group_id, target_date)
            keyboard = create_weekly_schedule_navigation_keyboard(target_date, group_id)

        if isinstance(query.message, Message):
            await query.message.edit_text(text, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
        elif query.inline_message_id:
            await bot.edit_message_text(text, inline_message_id=query.inline_message_id, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except TelegramBadRequest:
        pass 
    await query.answer()

@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action == "close"))
async def handle_close_schedule(query: CallbackQuery, callback_data: ScheduleCallbackFactory, bot: Bot):
    if isinstance(query.message, Message):
        try: await query.message.delete()
        except TelegramBadRequest: pass
    elif query.inline_message_id:
        try:
            if callback_data.schedule_type == "week":
                await bot.edit_message_text("Розклад на тиждень згорнуто", inline_message_id=query.inline_message_id, reply_markup=create_show_weekly_schedule_keyboard(callback_data.group_id))
            else:
                await bot.edit_message_text("Розклад згорнуто", inline_message_id=query.inline_message_id, reply_markup=create_show_schedule_keyboard(callback_data.group_id))
        except TelegramBadRequest: pass
    await query.answer()

@schedule_router.callback_query(ScheduleCallbackFactory.filter(F.action == "show"))
async def handle_show_schedule(query: CallbackQuery, callback_data: ScheduleCallbackFactory, services: BotServices, bot: Bot):
    if not query.inline_message_id: return await query.answer("Тільки для інлайн-розкладу.", show_alert=True)
    
    target_date = date.today()
    group_id = callback_data.group_id
    
    try:
        if callback_data.schedule_type == "week":
            text = services.format_weekly_schedule_by_group(group_id, target_date)
            keyboard = create_weekly_schedule_navigation_keyboard(target_date, group_id)
        else:
            text = services.format_daily_schedule_by_group(group_id, target_date)
            keyboard = create_schedule_navigation_keyboard(target_date, group_id)
            
        await bot.edit_message_text(text, inline_message_id=query.inline_message_id, reply_markup=keyboard, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception:
        await query.answer("Не вдалося розгорнути розклад.", show_alert=True)
    await query.answer()