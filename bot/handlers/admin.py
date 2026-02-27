import logging
import asyncio
import json

from bot.fsm import AdminFSM
from aiogram import F, Router, types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import BaseFilter
from aiogram.exceptions import TelegramBadRequest

from application.bot_services import BotServices
from bot.fsm import BroadcastFSM
from bot.keyboards import (
    create_admin_panel_keyboard, 
    create_broadcast_confirmation_keyboard,
    create_cancel_fsm_keyboard, 
    BroadcastCallbackFactory
)

logger = logging.getLogger(__name__)
admin_router = Router(name="admin_router")


class AdminFilter(BaseFilter):
    """Фільтр для перевірки, чи є користувач адміністратором локально (в db.json)."""
    async def __call__(
        self, 
        event: types.Message | types.CallbackQuery, 
        services: BotServices
    ) -> bool:
        if not event.from_user:
            return False
        
        user = services.get_user(event.from_user.id)
        return user is not None and user.get("is_admin", False)


@admin_router.message(F.text == "👑 Адмін-панель", AdminFilter())
async def handle_admin_panel(message: Message):
    """Відкриває головне меню адмін-панелі."""
    await message.answer("Вітаємо в адмін-панелі!", reply_markup=create_admin_panel_keyboard())
    try:
        await message.delete()
    except TelegramBadRequest:
        logger.warning("Could not delete user's admin panel request message.")


@admin_router.callback_query(F.data == "close_admin_panel", AdminFilter())
async def handle_close_admin_panel(query: CallbackQuery):
    """Закриває адмін-панель."""
    if isinstance(query.message, Message):
        try:
            await query.message.delete()
        except TelegramBadRequest:
            pass
    await query.answer()


@admin_router.callback_query(F.data == "start_broadcast", AdminFilter())
async def handle_start_broadcast(query: CallbackQuery, state: FSMContext):
    """Починає процес створення розсилки."""
    if isinstance(query.message, Message):
        await state.set_state(BroadcastFSM.getting_message)
        await query.message.edit_text(
            "Введіть текст повідомлення для розсилки (можна використовувати HTML-теги форматування):",
            reply_markup=create_cancel_fsm_keyboard()
        )
    await query.answer()


@admin_router.callback_query(BroadcastCallbackFactory.filter(F.action == "cancel"))
async def handle_cancel_fsm(query: CallbackQuery, state: FSMContext):
    """Скасовує будь-яку дію (розсилку або завантаження JSON) та очищує стан."""
    await state.clear()
    if isinstance(query.message, Message):
        await query.message.edit_text("Дію скасовано.")
    await query.answer()


@admin_router.message(BroadcastFSM.getting_message, AdminFilter())
async def handle_get_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Отримує текст від адміна, зберігає в стан і показує прев'ю."""
    if not message.text and not message.html_text:
        await message.reply("Будь ласка, надішліть текстове повідомлення.")
        return
    
    # Зберігаємо HTML-форматований текст
    message_text = message.html_text
    await state.update_data(message_text=message_text)
    await state.set_state(BroadcastFSM.confirming_broadcast)
    
    preview_text = "<b><u>Попередній перегляд розсилки</u></b>\n\n"
    preview_text += "🚀 <b>Тип відправки:</b> Негайно всім користувачам\n\n"
    preview_text += "<b>Текст повідомлення:</b>\n────────────────────\n"
    
    await message.answer(preview_text)
    await message.answer(
        message_text,
        reply_markup=create_broadcast_confirmation_keyboard(is_scheduled=False)
    )
    
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


@admin_router.callback_query(BroadcastFSM.confirming_broadcast, BroadcastCallbackFactory.filter(), AdminFilter())
async def handle_broadcast_confirmation(
    query: CallbackQuery, 
    callback_data: BroadcastCallbackFactory, 
    state: FSMContext,
    services: BotServices, 
    bot: Bot
):
    """Обробляє підтвердження розсилки (Надіслати / Редагувати / Скасувати)."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.")
        return

    # Прибираємо повідомлення з прев'ю
    try:
        await query.message.delete()
        preview_text_message_id = query.message.message_id - 1
        await bot.delete_message(query.message.chat.id, preview_text_message_id)
    except TelegramBadRequest:
        pass

    if callback_data.action == "edit_text":
        await state.set_state(BroadcastFSM.getting_message)
        await query.message.answer(
            "Введіть новий текст повідомлення:", 
            reply_markup=create_cancel_fsm_keyboard()
        )
        await query.answer()
        return

    if callback_data.action == "send":
        data = await state.get_data()
        message_text = data.get("message_text")
        
        if not message_text:
            await query.message.answer("❌ Помилка: текст повідомлення не знайдено. Спробуйте знову.")
            await state.clear()
            await query.answer()
            return

        await query.message.answer("🚀 Починаю розсилку. Це може зайняти деякий час...")
        
        users = services.db.get_all_users()
        success_count = 0
        failure_count = 0

        # Цикл відправки (локально перебираємо всіх юзерів)
        for user in users:
            try:
                await bot.send_message(
                    chat_id=user["telegram_id"],
                    text=message_text,
                    parse_mode="HTML"
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to send broadcast to user {user['telegram_id']}: {e}")
                failure_count += 1
            
            # Затримка 0.05 секунди (20 повідомлень на секунду), 
            # щоб Telegram не заблокував бота за флуд (Flood Control)
            await asyncio.sleep(0.05) 

        report_text = (
            f"✅ Розсилку успішно завершено!\n\n"
            f"🟢 Надіслано успішно: {success_count}\n"
            f"🔴 Помилок (юзер заблокував бота тощо): {failure_count}"
        )
        await query.message.answer(report_text)
        await state.clear()
        
    await query.answer()


@admin_router.callback_query(F.data == "upload_json", AdminFilter())
async def handle_upload_json_request(query: CallbackQuery, state: FSMContext):
    # Явна перевірка типу повідомлення для Pylance
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.")
        return

    await state.set_state(AdminFSM.waiting_for_json)
    await query.message.edit_text(
        "📂 Надішліть файл `db.json` з новим розкладом.\n\n"
        "<i>Увага: Бот оновить предмети, викладачів та розклад, але збереже всіх зареєстрованих користувачів.</i>",
        reply_markup=create_cancel_fsm_keyboard()
    )
    await query.answer()

@admin_router.message(AdminFSM.waiting_for_json, F.document, AdminFilter())
async def handle_json_document(message: Message, state: FSMContext, services: BotServices, bot: Bot):
    # 1. Перевіряємо, чи є документ і чи має він ім'я
    document = message.document
    if not document or not document.file_name or not document.file_name.endswith(".json"):
        await message.reply("❌ Будь ласка, надішліть файл у форматі .json")
        return

    file_id = document.file_id
    file = await bot.get_file(file_id)
    
    # 2. Перевіряємо, чи Telegram повернув шлях до файлу
    if not file.file_path:
        await message.reply("❌ Сталася помилка: Telegram не надав шлях до файлу.")
        return

    # Завантажуємо файл у пам'ять
    downloaded_file = await bot.download_file(file.file_path)
    
    # 3. Перевіряємо, чи файл успішно завантажився
    if not downloaded_file:
        await message.reply("❌ Не вдалося завантажити файл із серверів Telegram.")
        return

    # Читаємо вміст
    content = downloaded_file.read().decode('utf-8')

    try:
        new_data = json.loads(content)
        # Перевірка, чи це правильний файл (чи є там розклад)
        if "schedule_entries" not in new_data:
            raise ValueError("У файлі відсутній ключ 'schedule_entries'")
            
        await services.db.update_static_data(new_data)
        await message.reply("✅ Базу даних успішно оновлено! Розклад змінено.")
        await state.clear()
    except Exception as e:
        await message.reply(f"❌ Помилка читання файлу: {e}\nПеревірте синтаксис JSON.")


@admin_router.callback_query(F.data == "download_json", AdminFilter())
async def handle_download_json(query: CallbackQuery, services: BotServices):
    """Надсилає адміністратору поточний файл db.json."""
    if not isinstance(query.message, Message):
        await query.answer("Помилка: повідомлення недоступне.")
        return

    try:
        # Беремо шлях до файлу з нашого підключення до БД
        file_path = services.db.file_path
        
        # Створюємо об'єкт файлу для відправки через Telegram
        document = FSInputFile(file_path, filename="db.json")
        
        await query.message.answer_document(
            document=document,
            caption=(
                "📂 Ось поточна база даних вашого бота.\n\n"
                "Ви можете завантажити її, внести зміни у розклад чи викладачів, "
                "а потім повернути її боту за допомогою кнопки <b>'⬆️ Завантажити нову'</b>."
            )
        )
        await query.answer()
    except Exception as e:
        logger.exception("Failed to send db.json")
        await query.answer(f"Помилка при скачуванні файлу: {e}", show_alert=True)