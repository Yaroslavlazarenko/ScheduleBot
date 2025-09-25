import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions

from application.services.subject import SubjectService
from application.services.user import UserService 
from bot.keyboards import create_subjects_keyboard, SubjectCallbackFactory, create_subject_details_keyboard

logger = logging.getLogger(__name__)
subject_router = Router(name="subject_router")


@subject_router.message(F.text == "📚 Предмети")
async def handle_get_subjects_list(message: Message, subject_service: SubjectService):
    """Обробляє запит на отримання списку предметів."""
    subjects = await subject_service.get_all_subjects()
    
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
    subject_service: SubjectService,
    user_service: UserService
):
    """
    Обробляє вибір предмету та показує детальну інформацію про нього,
    відфільтровану для групи поточного користувача.
    """
    
    if callback_data.abbreviation is None or not isinstance(query.message, Message):
        await query.answer("Помилка: не вдалося обробити запит.", show_alert=True)
        return
    
    user = await user_service.get_user_by_telegram_id(query.from_user.id)
    if not user:
        await query.message.edit_text("❌ Помилка: не вдалося знайти ваші дані. Спробуйте /start.")
        await query.answer()
        return

    subject = await subject_service.get_grouped_subject_details(
        abbreviation=callback_data.abbreviation,
        group_id=user.group_id
    )

    if not subject:
        await query.message.edit_text("❌ Предмет не знайдено, або для вашої групи немає інформації.")
        await query.answer()
        return

    response_text = subject_service.format_subject_details(subject)
    keyboard = create_subject_details_keyboard()
    
    await query.message.edit_text(
        response_text, 
        reply_markup=keyboard,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )
    await query.answer()


@subject_router.callback_query(SubjectCallbackFactory.filter(F.action == "back"))
async def handle_back_to_subjects_list(
    query: CallbackQuery,
    subject_service: SubjectService
):
    """Обробляє натискання кнопки "Назад" і повертає до списку предметів."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    subjects = await subject_service.get_all_subjects()
    keyboard = create_subjects_keyboard(subjects)
    text = "Оберіть предмет, щоб переглянути детальну інформацію:"

    await query.message.edit_text(text=text, reply_markup=keyboard)
    await query.answer()


@subject_router.callback_query(SubjectCallbackFactory.filter(F.action == "close"))
async def handle_close_subjects_list(query: CallbackQuery):
    """Обробляє натискання кнопки "Закрити" і видаляє повідомлення."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
    
    try:
        await query.message.delete()
    except TelegramBadRequest:
        await query.message.edit_reply_markup(reply_markup=None)
    finally:
        await query.answer()