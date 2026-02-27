import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery 

from application.bot_services import BotServices
from bot.keyboards import (
    create_teachers_keyboard, 
    TeacherCallbackFactory, 
    create_teacher_details_keyboard
)

logger = logging.getLogger(__name__)
teacher_router = Router(name="teacher_router")


@teacher_router.message(F.text == "👨‍🏫 Вчителі")
async def handle_get_teachers_list(message: Message, services: BotServices):
    """Обробляє запит на отримання списку викладачів і видаляє повідомлення користувача."""
    teachers = services.db.get_teachers()
    
    if not teachers:
        await message.answer("На жаль, список викладачів порожній.")
        return

    keyboard = create_teachers_keyboard(teachers)
    await message.answer("Оберіть викладача, щоб переглянути детальну інформацію:", reply_markup=keyboard)

    try:
        await message.delete()
    except TelegramBadRequest as e:
        logger.warning("Could not delete user message: %s", e)


@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "select"))
async def handle_teacher_selection(
    query: CallbackQuery,
    callback_data: TeacherCallbackFactory,
    services: BotServices
):
    """Обробляє вибір викладача та показує детальну інформацію про нього з db.json."""
    if callback_data.id is None:
        await query.answer("Помилка: ID викладача не знайдено.", show_alert=True)
        return
    
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне для редагування.", show_alert=True)
        return
        
    # Шукаємо викладача в локальній базі
    teacher = next((t for t in services.db.get_teachers() if t["teacher_id"] == callback_data.id), None)

    if not teacher:
        await query.message.edit_text("❌ Викладача не знайдено. Можливо, його було видалено.")
        await query.answer()
        return

    # Формуємо текст
    caption_text = f"👨‍🏫 <b>{teacher['title']} {teacher['name']}</b>\n\n"
    contacts = teacher.get("contacts")
    if contacts:
        # Якщо контакти починаються з t.me або http, робимо клікабельне посилання
        if contacts.startswith("t.me/") or contacts.startswith("http"):
            # Додаємо https:// якщо потрібно, для коректного відображення в Telegram
            url = contacts if contacts.startswith("http") else f"https://{contacts}"
            caption_text += f"📞 <b>Контакти:</b> <a href='{url}'>{contacts}</a>"
        else:
            caption_text += f"📞 <b>Контакти:</b> {contacts}"
    else:
        caption_text += "<i>Контакти відсутні.</i>"

    photo_url = teacher.get("photo_url")
    keyboard = create_teacher_details_keyboard()
    
    try:
        if photo_url:
            # Якщо є фото, надсилаємо нове повідомлення з картинкою і видаляємо старе текстове
            await query.message.answer_photo(
                photo=photo_url,
                caption=caption_text,
                reply_markup=keyboard
            )
            await query.message.delete()
        else:
            # Якщо фото немає, просто редагуємо поточний текст
            await query.message.edit_text(caption_text, reply_markup=keyboard)

    except TelegramBadRequest as e:
        logger.error("Failed to send teacher info for teacher %d: %s", teacher["teacher_id"], e)
        # Якщо фото бите, відправляємо як текст
        await query.message.edit_text(
            f"{caption_text}\n\n<i>(Не вдалося завантажити фото)</i>",
            reply_markup=keyboard
        )
    finally:
        await query.answer()


@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "back"))
async def handle_back_to_teachers_list(
    query: CallbackQuery,
    services: BotServices
):
    """Обробляє натискання кнопки 'Назад' і повертає до списку викладачів."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    teachers = services.db.get_teachers()
    keyboard = create_teachers_keyboard(teachers)
    text = "Оберіть викладача, щоб переглянути детальну інформацію:"

    try:
        # Якщо попереднє повідомлення було з фото, його не можна відредагувати на текст
        if query.message.photo:
            await query.message.answer(text=text, reply_markup=keyboard)
            await query.message.delete()
        else:
            await query.message.edit_text(text=text, reply_markup=keyboard)
    except TelegramBadRequest as e:
        logger.warning("Could not go back to teachers list: %s", e)
    finally:
        await query.answer()


@teacher_router.callback_query(TeacherCallbackFactory.filter(F.action == "close"))
async def handle_close_teachers_list(query: CallbackQuery):
    """Обробляє натискання кнопки 'Закрити' у списку викладачів і видаляє повідомлення."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
    
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_reply_markup(reply_markup=None)
    finally:
        await query.answer()