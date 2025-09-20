import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from application.services import GroupService, UserService # +++ UPDATED LINE +++
from bot.fsm import RegistrationFSM
from bot.keyboards import create_groups_keyboard, create_main_keyboard # +++ UPDATED LINE +++

common_router = Router(name="common_router")
logger = logging.getLogger(__name__)


@common_router.message(CommandStart())
async def handle_start(
    message: Message, 
    group_service: GroupService, 
    user_service: UserService, # +++ NEW ARGUMENT +++
    state: FSMContext
):
    """
    Перевіряє, чи зареєстрований користувач. Якщо так, показує головне меню.
    Інакше починає процес реєстрації.
    """
    if not message.from_user:
        return
    
    # Перевірка, чи існує користувач
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if user:
        await message.answer(
            f"👋 З поверненням, {message.from_user.first_name}!\n\nОберіть дію:",
            reply_markup=create_main_keyboard()
        )
        return

    # Якщо користувач не знайдений, починаємо реєстрацію
    try:
        groups = await group_service.get_all_groups()
        if not groups:
            await message.answer("На жаль, зараз немає доступних груп для вибору. Спробуйте пізніше.")
            return

        keyboard = create_groups_keyboard(groups)
        await message.answer(
            '👋 Привіт! Я бот для роботи з розкладом.\n\n'
            'Для початку, будь ласка, оберіть вашу групу зі списку:',
            reply_markup=keyboard
        )
        await state.set_state(RegistrationFSM.choosing_group)

    except Exception:
        logger.exception("Error in handle_start")
        await message.answer('Сталася непередбачена помилка. Спробуйте почати знову: /start')