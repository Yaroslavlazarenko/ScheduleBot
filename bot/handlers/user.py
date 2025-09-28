import logging

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from api import ApiBadRequestError, ResourceNotFoundError
from application.services import GroupService, RegionService, UserService
from bot.fsm import RegistrationFSM
from bot.keyboards import (GroupCallbackFactory, RegionCallbackFactory, create_main_keyboard,
                           create_regions_keyboard)

logger = logging.getLogger(__name__)
user_router = Router(name="user_router")


@user_router.message(Command("groups"))
async def handle_get_groups(message: Message, group_service: GroupService):
    """Хендлер для отримання списку груп."""
    try:
        response_text = await group_service.format_groups_list()
        await message.answer(response_text)
    except Exception:
        logger.exception("Error in get_groups handler")
        await message.answer('Сталася непередбачена помилка під час отримання списку груп.')


@user_router.callback_query(RegistrationFSM.choosing_group, GroupCallbackFactory.filter())
async def handle_group_selection(
    query: types.CallbackQuery,
    callback_data: GroupCallbackFactory,
    state: FSMContext,
    region_service: RegionService
):
    """
    Обробляє вибір групи, зберігає його та запитує часовий пояс.
    """

    if not isinstance(query.message, Message):
        await query.answer("Не вдалося обробити натискання, повідомлення недоступне.")
        return
    
    await state.update_data(group_id=callback_data.id, group_name=callback_data.name)

    try:
        regions = await region_service.get_all_regions()
        if not regions:
            await query.message.edit_text("Помилка: не вдалося завантажити список часових поясів. Спробуйте пізніше.")
            await state.clear()
            return

        regions_map = {region.id: region.name for region in regions}
        await state.update_data(regions_map=regions_map)

        keyboard = create_regions_keyboard(regions)
        await query.message.edit_text(f"✅ Ви обрали групу: <b>{callback_data.name}</b>\n\n"
                                      "Тепер, будь ласка, оберіть ваш часовий пояс:",
                                      reply_markup=keyboard)
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
    user_service: UserService
):
    """
    Обробляє вибір регіону, завершує реєстрацію та надсилає головне меню.
    """
    if not isinstance(query.message, Message):
        await query.answer("Не вдалося обробити натискання, повідомлення недоступне.")
        return
    
    user_data = await state.get_data()
    group_id_str = str(user_data.get("group_id"))
    region_id_str = str(callback_data.id)

    user = query.from_user
    telegram_id = user.id
    username = user.username

    await query.message.edit_text("Реєструю вас...")

    try:
        response_text = await user_service.register_new_user(
            telegram_id=telegram_id,
            username=username,
            group_id_str=group_id_str,
            region_id_str=region_id_str
        )
        
        await query.message.edit_text(response_text)
        
        await query.message.answer(
            f"Чудово, {user.first_name}! Тепер ви можете користуватися ботом. Оберіть дію з меню нижче:",
            reply_markup=create_main_keyboard(is_admin=False)
        )

    except ValueError as e:
        await query.message.edit_text(str(e))
    except ResourceNotFoundError:
        await query.message.edit_text("❌ Сталася дивна помилка: обрану групу або регіон не знайдено. Спробуйте /start.")
    except ApiBadRequestError:
        await query.message.edit_text("⚠️ Ви вже були зареєстровані.")
        await query.message.answer(
            "Оберіть дію з меню:",
            reply_markup=create_main_keyboard(is_admin=False)
        )
    except Exception:
        await query.message.edit_text("Сталася непередбачена помилка. Спробуйте пізніше.")
    finally:
        await state.clear()
        await query.answer()