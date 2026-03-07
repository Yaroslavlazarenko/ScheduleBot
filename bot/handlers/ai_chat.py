import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, LinkPreviewOptions
from aiogram.enums import ChatAction, ParseMode

from application.bot_services import BotServices
from application.ai_service import AIService

# ДОДАНО: імпорт create_main_keyboard
from bot.keyboards import create_schedule_navigation_keyboard, create_main_keyboard

logger = logging.getLogger(__name__)
ai_router = Router(name="ai_router")

@ai_router.message(F.text)
async def handle_ai_chat(message: Message, services: BotServices, bot: Bot):
    if not message.from_user or not message.text:
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    
    ai_service = AIService(services=services)
    
    response_text, ui_action = await ai_service.process_user_message(
        telegram_id=message.from_user.id,
        text=message.text
    )
    
    response_text = response_text.replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "\n")
    response_text = response_text.replace("**", "") 
    
    # === ДОДАНО: Генеруємо актуальну клавіатуру для юзера ===
    user = services.get_user(message.from_user.id)
    is_admin = user.get("is_admin", False) if user else False
    main_keyboard = create_main_keyboard(is_admin=is_admin)
    
    # 1. Відправляємо текстову відповідь від ШІ + ОНОВЛЮЄМО КЛАВІАТУРУ
    try:
        await message.reply(response_text, parse_mode=ParseMode.HTML, reply_markup=main_keyboard)
    except Exception as e:
        logger.error(f"Помилка відправки HTML від ШІ: {e}\nТекст був: {response_text}")
        await message.reply(response_text, parse_mode=None, reply_markup=main_keyboard)

    # 2. Якщо ШІ викликав тул розкладу, надсилаємо ПОВНОЦІННЕ МЕНЮ РОЗКЛАДУ
    if ui_action and ui_action.get("type") == "schedule":
        target_date = ui_action.get("date")
        
        if user and target_date:
            group_id = user["group_id"]
            
            schedule_menu_text = services.format_daily_schedule_by_group(group_id, target_date)
            keyboard = create_schedule_navigation_keyboard(target_date, group_id)
            
            await message.answer(
                text=schedule_menu_text,
                reply_markup=keyboard,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                parse_mode=ParseMode.HTML
            )