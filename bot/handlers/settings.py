import logging

from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from application.services import GroupService, RegionService, UserService
from bot.fsm import SettingsFSM
from bot.keyboards import (GroupCallbackFactory, RegionCallbackFactory,
                           SettingsCallbackFactory, create_groups_keyboard,
                           create_regions_keyboard, create_settings_keyboard)

logger = logging.getLogger(__name__)
settings_router = Router(name="settings_router")


@settings_router.message(F.text == "⚙️ Налаштування")
async def handle_settings(message: Message):
    """Обробляє запит на відкриття меню налаштувань."""
    await message.answer(
        "Оберіть, що бажаєте змінити:",
        reply_markup=create_settings_keyboard()
    )
    try:
        await message.delete()
    except TelegramBadRequest:
        logger.warning("Could not delete user's settings request message.")


@settings_router.callback_query(SettingsCallbackFactory.filter(F.action == "close"))
async def handle_close_settings(query: types.CallbackQuery):
    """Обробляє закриття меню налаштувань."""
    if isinstance(query.message, Message):
        try:
            await query.message.delete()
        except TelegramBadRequest:
            await query.message.edit_reply_markup(reply_markup=None)
    await query.answer()


@settings_router.callback_query(SettingsCallbackFactory.filter(F.action == "change_group"))
async def handle_change_group_request(
    query: types.CallbackQuery,
    state: FSMContext,
    group_service: GroupService
):
    """Починає процес зміни групи."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    groups = await group_service.get_all_groups()
    if not groups:
        await query.message.edit_text("На жаль, зараз немає доступних груп для вибору.")
        await query.answer()
        return

    keyboard = create_groups_keyboard(groups)
    await query.message.edit_text(
        'Будь ласка, оберіть вашу нову групу зі списку:',
        reply_markup=keyboard
    )
    await state.set_state(SettingsFSM.choosing_group)
    await query.answer()


@settings_router.callback_query(SettingsFSM.choosing_group, GroupCallbackFactory.filter())
async def handle_new_group_selection(
    query: types.CallbackQuery,
    callback_data: GroupCallbackFactory,
    state: FSMContext,
    user_service: UserService
):
    """Обробляє вибір нової групи та оновлює дані користувача."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
        
    await query.message.edit_text("Оновлюю вашу групу...")
    try:
        await user_service.change_user_group(
            telegram_id=query.from_user.id,
            new_group_id=callback_data.id
        )
        await query.message.edit_text(f"✅ Вашу групу успішно змінено на <b>{callback_data.name}</b>.")
    except Exception as e:
        logger.exception("Failed to change user group for user %d", query.from_user.id)
        await query.message.edit_text(f"❌ Сталася помилка під час зміни групи: {e}")
    finally:
        await state.clear()
        await query.answer()


@settings_router.callback_query(SettingsCallbackFactory.filter(F.action == "change_region"))
async def handle_change_region_request(
    query: types.CallbackQuery,
    state: FSMContext,
    region_service: RegionService
):
    """Починає процес зміни часового поясу."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return
        
    regions = await region_service.get_all_regions()
    if not regions:
        await query.message.edit_text("Помилка: не вдалося завантажити список часових поясів.")
        await query.answer()
        return

    keyboard = create_regions_keyboard(regions)
    await query.message.edit_text(
        'Будь ласка, оберіть ваш новий часовий пояс:',
        reply_markup=keyboard
    )
    await state.set_state(SettingsFSM.choosing_region)
    await query.answer()


@settings_router.callback_query(SettingsFSM.choosing_region, RegionCallbackFactory.filter())
async def handle_new_region_selection(
    query: types.CallbackQuery,
    callback_data: RegionCallbackFactory,
    state: FSMContext,
    user_service: UserService,
    region_service: RegionService
):
    """Обробляє вибір нового часового поясу та оновлює дані користувача."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.", show_alert=True)
        return

    await query.message.edit_text("Оновлюю ваш часовий пояс...")
    try:
        await user_service.change_user_region(
            telegram_id=query.from_user.id,
            new_region_id=callback_data.id
        )
        regions = await region_service.get_all_regions()
        region_name = next((r.name for r in regions if r.id == callback_data.id), "невідомий")
        
        await query.message.edit_text(f"✅ Ваш часовий пояс успішно змінено на <b>{region_name}</b>.")
    except Exception as e:
        logger.exception("Failed to change user region for user %d", query.from_user.id)
        await query.message.edit_text(f"❌ Сталася помилка під час зміни часового поясу: {e}")
    finally:
        await state.clear()
        await query.answer()