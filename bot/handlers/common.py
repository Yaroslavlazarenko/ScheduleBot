import logging
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from application.bot_services import BotServices
from bot.fsm import RegistrationFSM
from bot.keyboards import create_groups_keyboard, create_main_keyboard


common_router = Router(name="common_router")
logger = logging.getLogger(__name__)

@common_router.message(F.text.in_({"☕ Зробити каву", "☕️ Зробити каву"}))
async def handle_make_coffee(message: Message):
    """Жартівлива команда для видачі кави."""
    await message.answer(
        "Ось ваша гаряча кава! ☕️🍩\n"
        "Бажаю продуктивного дня та енергії для навчання!"
    )

@common_router.message(CommandStart())
async def handle_start(
    message: Message, 
    services: BotServices,
    state: FSMContext
):
    """
    Перевіряє, чи зареєстрований користувач локально (у db.json).
    Якщо так, показує головне меню.
    Інакше починає процес реєстрації.
    Після відповіді видаляє команду /start, щоб не засмічувати чат.
    """
    if not message.from_user:
        return
    
    try:
        # Шукаємо користувача в локальній базі
        user = services.get_user(message.from_user.id)
        
        if user:
            # Юзер знайдений -> показуємо меню.
            # Звертаємося до словника через .get(), щоб безпечно отримати поле is_admin
            is_admin = user.get("is_admin", False)
            
            await message.answer(
                f"👋 З поверненням, {message.from_user.first_name}!\n\nОберіть дію:",
                reply_markup=create_main_keyboard(is_admin=is_admin)
            )
        else:
            # Юзер не знайдений -> починаємо реєстрацію
            groups = services.get_all_groups()
            
            if not groups:
                await message.answer("На жаль, зараз немає доступних груп для вибору. Зверніться до адміністратора.")
            else:
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
    finally:
        # Спроба видалити команду /start (щоб чат був чистим)
        try:
            await message.delete()
        except TelegramBadRequest as e:
            logger.warning("Could not delete user's /start message: %s", e)