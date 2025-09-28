import logging
from datetime import datetime, timezone

from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import BaseFilter
from aiogram.exceptions import TelegramBadRequest

from application.services import UserService, BroadcastService
from bot.fsm import BroadcastFSM
from bot.keyboards import (create_admin_panel_keyboard, create_broadcast_confirmation_keyboard,
                           create_cancel_fsm_keyboard, create_broadcast_type_keyboard)
from bot.keyboards import BroadcastCallbackFactory

logger = logging.getLogger(__name__)
admin_router = Router(name="admin_router")

class AdminFilter(BaseFilter):
    async def __call__(self, event: types.Message | types.CallbackQuery, user_service: UserService) -> bool:
        if not event.from_user:
            return False
        user = await user_service.get_user_by_telegram_id(event.from_user.id)
        return user is not None and user.is_admin

@admin_router.message(F.text == "👑 Адмін-панель", AdminFilter())
async def handle_admin_panel(message: Message):
    await message.answer("Вітаємо в адмін-панелі!", reply_markup=create_admin_panel_keyboard())
    await message.delete()

@admin_router.callback_query(F.data == "close_admin_panel", AdminFilter())
async def handle_close_admin_panel(query: CallbackQuery):
    if isinstance(query.message, Message):
        try:
            await query.message.delete()
        except TelegramBadRequest:
            logger.warning("Could not delete admin panel message.")
    await query.answer()

@admin_router.callback_query(F.data == "start_broadcast", AdminFilter())
async def handle_start_broadcast(query: CallbackQuery, state: FSMContext):
    if isinstance(query.message, Message):
        await state.set_state(BroadcastFSM.choosing_type)
        await query.message.edit_text(
            "Оберіть тип розсилки:",
            reply_markup=create_broadcast_type_keyboard()
        )
    await query.answer()

@admin_router.callback_query(BroadcastFSM(), BroadcastCallbackFactory.filter(F.action == "cancel"))
async def handle_cancel_fsm(query: CallbackQuery, state: FSMContext):
    await state.clear()
    if isinstance(query.message, Message):
        await query.message.edit_text("Дію скасовано.")
    await query.answer()

@admin_router.callback_query(BroadcastFSM.choosing_type, BroadcastCallbackFactory.filter(F.action.in_({"send_now", "schedule"})))
async def handle_broadcast_type(query: CallbackQuery, state: FSMContext, callback_data: BroadcastCallbackFactory):
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.")
        return

    if callback_data.action == "send_now":
        await state.update_data(is_scheduled=False)
        await state.set_state(BroadcastFSM.getting_message)
        await query.message.edit_text(
            "Введіть текст повідомлення для негайної розсилки:",
            reply_markup=create_cancel_fsm_keyboard()
        )
    elif callback_data.action == "schedule":
        await state.update_data(is_scheduled=True)
        await state.set_state(BroadcastFSM.getting_schedule_time)
        await query.message.edit_text(
            "Введіть дату та час для відправки у форматі `РРРР-ММ-ДД ГГ:ХХ` (UTC).\n\n"
            "Наприклад: `2024-09-01 08:30`",
            reply_markup=create_cancel_fsm_keyboard(),
            parse_mode="Markdown"
        )
    await query.answer()

@admin_router.message(BroadcastFSM.getting_schedule_time)
async def handle_get_schedule_time(message: Message, state: FSMContext):
    if not message.text:
        await message.reply("Будь ласка, надішліть час у текстовому форматі.")
        return

    try:
        schedule_dt_naive = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
        schedule_dt_utc = schedule_dt_naive.replace(tzinfo=timezone.utc)

        if schedule_dt_utc <= datetime.now(timezone.utc):
            await message.reply("❌ Помилка: вказаний час вже минув. Введіть майбутню дату та час.")
            return

        await state.update_data(schedule_time=schedule_dt_utc)
        await state.set_state(BroadcastFSM.getting_message)
        await message.answer(
            f"✅ Час заплановано на {schedule_dt_utc.strftime('%Y-%m-%d %H:%M %Z')}.\n\n"
            "Тепер введіть текст повідомлення:",
            reply_markup=create_cancel_fsm_keyboard()
        )

    except ValueError:
        await message.reply("❌ Неправильний формат. Будь ласка, введіть дату та час у форматі `РРРР-ММ-ДД ГГ:ХХ`.")
    finally:
        try:
            await message.delete()
        except TelegramBadRequest:
            logger.warning("Could not delete user's time input message.")


async def show_confirmation_preview(bot: Bot, chat_id: int, state: FSMContext):
    """Вспомогательная функция для отображения превью."""
    data = await state.get_data()
    message_text = data.get("message_text", "Текст не встановлено.")
    is_scheduled = data.get("is_scheduled", False)
    schedule_time: datetime | None = data.get("schedule_time")

    preview_text = "<b><u>Попередній перегляд розсилки</u></b>\n\n"
    if is_scheduled and schedule_time:
        preview_text += f"🕒 <b>Заплановано на:</b> {schedule_time.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
    else:
        preview_text += "🚀 <b>Тип відправки:</b> Негайно\n\n"
    
    preview_text += "<b>Текст повідомлення:</b>\n────────────────────\n"
    
    await bot.send_message(chat_id, preview_text)
    await bot.send_message(
        chat_id,
        message_text,
        reply_markup=create_broadcast_confirmation_keyboard(is_scheduled=is_scheduled)
    )

@admin_router.message(BroadcastFSM.getting_message)
async def handle_get_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.reply("Будь ласка, надішліть текст для розсилки.")
        return
    
    await state.update_data(message_text=message.html_text)
    await state.set_state(BroadcastFSM.confirming_broadcast)
    await show_confirmation_preview(bot, message.chat.id, state)
    try:
        await message.delete()
    except TelegramBadRequest:
        logger.warning("Could not delete user's broadcast text message.")

@admin_router.callback_query(BroadcastFSM.confirming_broadcast, BroadcastCallbackFactory.filter())
async def handle_broadcast_confirmation(
    query: CallbackQuery, callback_data: BroadcastCallbackFactory, state: FSMContext,
    broadcast_service: BroadcastService, bot: Bot
):
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне для взаємодії.")
        return

    try:
        await query.message.delete()
        if query.message.reply_to_message:
            await bot.delete_message(query.message.chat.id, query.message.reply_to_message.message_id)
    except TelegramBadRequest:
        logger.warning("Could not delete preview messages.")

    if callback_data.action == "edit_text":
        await state.set_state(BroadcastFSM.getting_message)
        await query.message.answer("Введіть новий текст повідомлення:", reply_markup=create_cancel_fsm_keyboard())
    
    elif callback_data.action == "edit_time":
        await state.set_state(BroadcastFSM.getting_schedule_time)
        await query.message.answer(
            "Введіть нову дату та час для відправки у форматі `РРРР-ММ-ДД ГГ:ХХ` (UTC):",
            reply_markup=create_cancel_fsm_keyboard(),
            parse_mode="Markdown"
        )

    elif callback_data.action == "send":
        data = await state.get_data()
        message_text = data.get("message_text")
        schedule_time_obj: datetime | None = data.get("schedule_time")
        
        schedule_time_iso = schedule_time_obj.isoformat() if schedule_time_obj else None
        
        if not message_text:
            await query.message.answer("❌ Помилка: текст повідомлення не знайдено. Спробуйте знову.")
        else:
            result_message = await broadcast_service.create_broadcast(message_text, schedule_time_iso)
            await query.message.answer(result_message)
        
        await state.clear()
        
    await query.answer()