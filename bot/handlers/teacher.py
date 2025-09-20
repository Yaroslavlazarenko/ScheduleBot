import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery 

from application.services.teacher import TeacherService
from bot.keyboards import create_teachers_keyboard, TeacherCallbackFactory, create_teacher_details_keyboard

logger = logging.getLogger(__name__)
teacher_router = Router(name="teacher_router")

@teacher_router.message(F.text == "👨‍🏫 Вчителі")
async def handle_get_teachers_list(message: Message, teacher_service: TeacherService):
    """Обробляє запит на отримання списку викладачів і видаляє повідомлення користувача."""
    teachers = await teacher_service.get_all_teachers()
    
    if not teachers:
        await message.answer("На жаль, список викладачів порожній.")
        return

    keyboard = create_teachers_keyboard(teachers)
    await message.answer("Оберіть викладача, щоб переглянути детальну інформацію:", reply_markup=keyboard)

    try:
        await message.delete()
    except TelegramBadRequest as e:
        logger.warning("Could not delete user message: %s", e)

@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "back"))
async def handle_back_to_teachers_list(
    query: CallbackQuery,
    teacher_service: TeacherService
):
    """Обробляє натискання кнопки "Назад" і повертає до списку викладачів."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    teachers = await teacher_service.get_all_teachers()
    keyboard = create_teachers_keyboard(teachers)
    text = "Оберіть викладача, щоб переглянути детальну інформацію:"

    await query.message.answer(text=text, reply_markup=keyboard)

    try:
        await query.message.delete()
    except TelegramBadRequest as e:
        logger.warning("Could not delete message on 'back' action: %s", e)
    finally:
        await query.answer()

@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "select"))
async def handle_teacher_selection(
    query: CallbackQuery,
    callback_data: TeacherCallbackFactory,
    teacher_service: TeacherService
):
    """Обробляє вибір викладача та показує детальну інформацію про нього."""
    
    if callback_data.id is None:
        await query.answer("Помилка: ID викладача не знайдено.", show_alert=True)
        logger.warning("Teacher selection callback received without a teacher ID.")
        return
    
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне для редагування.", show_alert=True)
        return
        
    teacher = await teacher_service.get_teacher_by_id(callback_data.id)

    if not teacher:
        await query.message.edit_text("❌ Викладача не знайдено. Можливо, його було видалено.")
        await query.answer()
        return

    photo_url, other_infos = teacher_service.extract_photo_and_infos(teacher)

    caption_text = teacher_service.format_teacher_details(teacher, other_infos)

    keyboard = create_teacher_details_keyboard()
    
    try:
        if photo_url:
            await query.message.answer_photo(
                photo=photo_url,
                caption=caption_text,
                reply_markup=keyboard
            )
            await query.message.delete()
        else:
            await query.message.edit_text(caption_text, reply_markup=keyboard)

    except TelegramBadRequest as e:
        logger.error("Failed to send teacher info for teacher %d: %s", teacher.id, e)
        await query.message.edit_text(
            f"{caption_text}\n\n<i>(Не вдалося завантажити фото)</i>",
            reply_markup=keyboard
        )
    finally:
        await query.answer()

@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "close"))
async def handle_close_teachers_list(query: CallbackQuery):
    """Обробляє натискання кнопки "Назад" у списку викладачів і видаляє повідомлення."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
    
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_reply_markup(reply_markup=None)
    finally:
        await query.answer()