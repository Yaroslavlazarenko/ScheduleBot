import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from application.bot_services import BotServices
from bot.fsm import RegistrationFSM
from bot.keyboards import (
    GroupCallbackFactory, 
    RegionCallbackFactory, 
    create_main_keyboard,
    create_regions_keyboard
)

logger = logging.getLogger(__name__)
user_router = Router(name="user_router")


@user_router.message(Command("groups"))
async def handle_get_groups(message: Message, services: BotServices):
    """Допоміжна команда для перегляду списку всіх доступних груп."""
    try:
        groups = services.get_all_groups()
        if not groups:
            await message.answer("Список груп порожній.")
            return
            
        text = "<b>Список доступних груп:</b>\n\n"
        text += "\n".join([f"• <code>{g['name']}</code> (ID: {g['group_id']})" for g in groups])
        await message.answer(text)
    except Exception:
        logger.exception("Error in get_groups handler")
        await message.answer('Сталася непередбачена помилка під час отримання списку груп.')


@user_router.callback_query(RegistrationFSM.choosing_group, GroupCallbackFactory.filter())
async def handle_group_selection(
    query: types.CallbackQuery,
    callback_data: GroupCallbackFactory,
    state: FSMContext,
    services: BotServices
):
    """
    Обробляє вибір групи, зберігає його у FSM та пропонує обрати часовий пояс.
    """
    if not isinstance(query.message, Message):
        await query.answer("Не вдалося обробити натискання, повідомлення недоступне.")
        return
    
    # Зберігаємо ID обраної групи в пам'ять (FSM)
    await state.update_data(group_id=callback_data.id)

    try:
        regions = services.get_all_regions()
        if not regions:
            await query.message.edit_text("Помилка: не вдалося завантажити список часових поясів. Спробуйте пізніше.")
            await state.clear()
            return

        keyboard = create_regions_keyboard(regions)
        await query.message.edit_text(
            f"✅ Ви обрали групу: <b>{callback_data.name}</b>\n\n"
            "Тепер, будь ласка, оберіть ваш часовий пояс:",
            reply_markup=keyboard
        )
        
        # Переводимо бота в стан очікування вибору регіону
        await state.set_state(RegistrationFSM.choosing_region)
        
    except Exception:
        logger.exception("Failed to get regions")
        await query.message.edit_text("Сталася помилка під час завантаження часових поясів. Спробуйте почати знову: /start")
        await state.clear()
    finally:
        await query.answer()


@user_router.callback_query(RegistrationFSM.choosing_region, RegionCallbackFactory.filter())
async def handle_region_selection(
    query: types.CallbackQuery,
    callback_data: RegionCallbackFactory,
    state: FSMContext,
    services: BotServices
):
    """
    Обробляє вибір регіону, завершує реєстрацію (записує в db.json) 
    та надсилає головне меню бота.
    """
    if not isinstance(query.message, Message):
        await query.answer("Не вдалося обробити натискання, повідомлення недоступне.")
        return
    
    # Дістаємо ID групи, яке ми зберегли на попередньому кроці
    user_data = await state.get_data()
    group_id = user_data.get("group_id")

    # ДОДАНО: Перевірка на те, чи існує group_id і чи є він числом
    if not isinstance(group_id, int):
        await query.message.edit_text("❌ Помилка: дані сесії втрачено. Будь ласка, почніть реєстрацію знову: /start")
        await state.clear()
        await query.answer()
        return

    user = query.from_user
    telegram_id = user.id
    username = user.username or ""

    await query.message.edit_text("Реєструю вас...")

    try:
        # Реєструємо користувача в JSON базі даних
        response_text = await services.register_user(
            telegram_id=telegram_id,
            username=username,
            group_id=group_id,
            region_id=callback_data.id
        )
        
        await query.message.edit_text(response_text)
        
        # Видаємо клавіатуру. Початково is_admin = False для всіх нових юзерів
        await query.message.answer(
            f"Чудово, {user.first_name}! Тепер ви можете користуватися ботом. Оберіть дію з меню нижче:",
            reply_markup=create_main_keyboard(is_admin=False)
        )

    except Exception:
        logger.exception("Registration error")
        await query.message.edit_text("Сталася непередбачена помилка. Спробуйте пізніше.")
    finally:
        # Обов'язково очищуємо стан FSM після успішної чи неуспішної реєстрації
        await state.clear()
        await query.answer()