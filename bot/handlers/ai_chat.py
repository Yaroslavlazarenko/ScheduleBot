import logging
from aiogram import Router, F, Bot # <-- ДОДАНО імпорт Bot
from aiogram.types import Message, LinkPreviewOptions
from aiogram.enums import ChatAction, ParseMode

from application.bot_services import BotServices
from application.ai_service import AIService

from bot.keyboards import create_schedule_navigation_keyboard

logger = logging.getLogger(__name__)
ai_router = Router(name="ai_router")

@ai_router.message(F.text)
# ДОДАНО параметр bot: Bot у функцію
async def handle_ai_chat(message: Message, services: BotServices, bot: Bot):
    """Обробляє всі текстові повідомлення, які не підпадають під інші хендлери, надсилаючи їх до ШІ."""
    if not message.from_user or not message.text:
        return

    # ТЕПЕР використовуємо напряму об'єкт bot, Pylance буде задоволений
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    ai_service = AIService(services=services)
    
    response_text, ui_action = await ai_service.process_user_message(
        telegram_id=message.from_user.id,
        text=message.text
    )
    
    # Замінюємо HTML-перенесення рядка на звичайні
    response_text = response_text.replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "\n")
    response_text = response_text.replace("**", "") 
    
    # 1. Відправляємо текстову відповідь від ШІ
    try:
        await message.reply(response_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Помилка відправки HTML від ШІ: {e}\nТекст був: {response_text}")
        await message.reply(response_text, parse_mode=None)

    # 2. Якщо ШІ викликав тул розкладу, надсилаємо ПОВНОЦІННЕ МЕНЮ РОЗКЛАДУ
    if ui_action and ui_action.get("type") == "schedule":
        target_date = ui_action.get("date")
        user = services.get_user(message.from_user.id)
        
        if user and target_date:
            group_id = user["group_id"]
            
            # Генеруємо текст меню розкладу
            schedule_menu_text = services.format_daily_schedule_by_group(group_id, target_date)
            # Генеруємо клавіатуру з кнопками вліво/вправо
            keyboard = create_schedule_navigation_keyboard(target_date, group_id)
            
            # Відправляємо окремим повідомленням під відповіддю ШІ
            await message.answer(
                text=schedule_menu_text,
                reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                parse_mode=ParseMode.HTML
            )