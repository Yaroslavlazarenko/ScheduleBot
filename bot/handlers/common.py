import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from application.services import GroupService
from bot.fsm import RegistrationFSM
from bot.keyboards import create_groups_keyboard

common_router = Router(name="common_router")
logger = logging.getLogger(__name__)


@common_router.message(CommandStart())
async def handle_start(message: Message, group_service: GroupService, state: FSMContext):
    """
    Починає процес реєстрації користувача, запитуючи його групу.
    """
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