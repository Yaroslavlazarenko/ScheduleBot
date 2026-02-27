import logging
from datetime import date
from uuid import uuid4
from aiogram import Bot, Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent, LinkPreviewOptions
from application.bot_services import BotServices
from bot.keyboards import create_schedule_navigation_keyboard, create_weekly_schedule_navigation_keyboard

logger = logging.getLogger(__name__)
inline_router = Router(name="inline_router")

@inline_router.inline_query()
async def handle_inline_query(query: InlineQuery, services: BotServices, bot: Bot):
    search_text = query.query.strip().lower()
    all_groups = services.get_all_groups()
    
    # Фільтруємо групи за тим, що ввів юзер
    if search_text:
        filtered_groups = [g for g in all_groups if search_text in g["name"].lower()]
    else:
        filtered_groups = all_groups

    # Щоб група самого юзера завжди була першою в списку (якщо він зареєстрований)
    user = services.get_user(query.from_user.id)
    user_group_id = user["group_id"] if user else None
    
    if not search_text and user_group_id:
        filtered_groups.sort(key=lambda g: 0 if g["group_id"] == user_group_id else 1)

    results = []
    today = date.today()

    for group in filtered_groups:
        group_id = group["group_id"]
        group_name = group["name"]

        # 1. Розклад на день
        daily_text = services.format_daily_schedule_by_group(group_id, today)
        daily_kb = create_schedule_navigation_keyboard(today, group_id)
        
        results.append(InlineQueryResultArticle(
            id=f"daily_{group_id}_{uuid4().hex[:8]}",
            title=f"🗓 На сьогодні | {group_name}",
            description=f"Надіслати розклад групи {group_name} на сьогодні",
            input_message_content=InputTextMessageContent(
                message_text=daily_text, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True)
            ),
            reply_markup=daily_kb
        ))

        # 2. Розклад на тиждень
        weekly_text = services.format_weekly_schedule_by_group(group_id, today)
        weekly_kb = create_weekly_schedule_navigation_keyboard(today, group_id)
        
        results.append(InlineQueryResultArticle(
            id=f"weekly_{group_id}_{uuid4().hex[:8]}",
            title=f"📅 На тиждень | {group_name}",
            description=f"Надіслати розклад групи {group_name} на цей тиждень",
            input_message_content=InputTextMessageContent(
                message_text=weekly_text, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True)
            ),
            reply_markup=weekly_kb
        ))

    # Відправляємо результати (cache_time=1 робить пошук більш чутливим до тексту)
    await query.answer(results=results, cache_time=1, is_personal=True)