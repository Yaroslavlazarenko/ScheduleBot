import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions

from application.bot_services import BotServices
from bot.keyboards import create_subjects_keyboard, SubjectCallbackFactory, create_subject_details_keyboard

logger = logging.getLogger(__name__)
subject_router = Router(name="subject_router")


@subject_router.message(F.text == "📚 Предмети")
async def handle_get_subjects_list(message: Message, services: BotServices):
    """Обробляє запит на отримання списку предметів."""
    subjects = services.db.get_subjects()
    
    if not subjects:
        await message.answer("На жаль, список предметів порожній.")
        return

    keyboard = create_subjects_keyboard(subjects)
    await message.answer("Оберіть предмет, щоб переглянути детальну інформацію:", reply_markup=keyboard)

    try:
        await message.delete()
    except TelegramBadRequest as e:
        logger.warning("Could not delete user message: %s", e)


@subject_router.callback_query(SubjectCallbackFactory.filter(F.action == "select"))
async def handle_subject_selection(
    query: CallbackQuery,
    callback_data: SubjectCallbackFactory,
    services: BotServices
):
    """
    Обробляє вибір предмету та показує детальну інформацію про нього,
    включаючи викладачів, які ведуть його для групи поточного користувача.
    """
    if callback_data.subject_name_id is None or not isinstance(query.message, Message):
        await query.answer("Помилка: не вдалося обробити запит.", show_alert=True)
        return
    
    # Знаходимо сам предмет
    subject_id = callback_data.subject_name_id
    subject = next((s for s in services.db.get_subjects() if s["subject_id"] == subject_id), None)

    if not subject:
        await query.message.edit_text("❌ Предмет не знайдено.")
        await query.answer()
        return

    text = f"📚 <b>{subject['full_name']}</b>\n"
    text += f"🔖 <b>Абревіатура:</b> {subject['abbreviation']}\n"

    # Отримуємо дані користувача, щоб дізнатися його групу
    user = services.get_user(query.from_user.id)
    if user:
        group_id = user["group_id"]
        
        # Шукаємо всі записи в розкладі для цієї групи та цього предмету
        schedule_entries = [
            e for e in services.db.data.get("schedule_entries", [])
            if e["subject_id"] == subject_id and e["group_id"] == group_id
        ]

        if schedule_entries:
            text += "\n👨‍🏫 <b>Викладачі курсу (для вашої групи):</b>\n"
            
            # Збираємо унікальних викладачів та типи пар (лекція/практика), які вони ведуть
            teacher_map = {}
            for entry in schedule_entries:
                t_id = entry["teacher_id"]
                c_type = entry["class_type"]
                if t_id not in teacher_map:
                    teacher_map[t_id] = set()
                teacher_map[t_id].add(c_type)

            for t_id, types_set in teacher_map.items():
                teacher = next((t for t in services.db.get_teachers() if t["teacher_id"] == t_id), None)
                if teacher:
                    types_str = ", ".join(types_set)
                    text += f"• {teacher['title']} {teacher['name']} <i>({types_str})</i>\n"
        else:
            text += "\n<i>Для вашої групи цей предмет не знайдено у розкладі.</i>"

    keyboard = create_subject_details_keyboard()
    
    try:
        await query.message.edit_text(
            text, 
            reply_markup=keyboard,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    except TelegramBadRequest:
        pass # Ігноруємо, якщо текст не змінився
        
    await query.answer()


@subject_router.callback_query(SubjectCallbackFactory.filter(F.action == "back"))
async def handle_back_to_subjects_list(query: CallbackQuery, services: BotServices):
    """Обробляє натискання кнопки 'Назад' і повертає до списку предметів."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    subjects = services.db.get_subjects()
    keyboard = create_subjects_keyboard(subjects)
    text = "Оберіть предмет, щоб переглянути детальну інформацію:"

    try:
        await query.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest:
        pass
        
    await query.answer()


@subject_router.callback_query(SubjectCallbackFactory.filter(F.action == "close"))
async def handle_close_subjects_list(query: CallbackQuery):
    """Обробляє натискання кнопки 'Закрити' і видаляє повідомлення."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
    
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_reply_markup(reply_markup=None)
    finally:
        await query.answer()