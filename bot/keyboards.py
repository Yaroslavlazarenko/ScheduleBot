from typing import List
from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, 
                           KeyboardButton, ReplyKeyboardMarkup)

from api import ApiGroupDTO, ApiRegionDTO

class GroupCallbackFactory(CallbackData, prefix="group"):
    id: int
    name: str

class RegionCallbackFactory(CallbackData, prefix="region"):
    id: int

class ScheduleCallbackFactory(CallbackData, prefix="schedule"):
    action: str
    current_date: str

def create_main_keyboard() -> ReplyKeyboardMarkup:
    """Створює головну клавіатуру з основними діями."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗓 Отримати розклад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def create_schedule_navigation_keyboard(current_date: date) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для навігації по днях розкладу."""
    date_str = current_date.isoformat()
    buttons = [
        InlineKeyboardButton(
            text="⬅️",
            callback_data=ScheduleCallbackFactory(action="prev", current_date=date_str).pack()
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=ScheduleCallbackFactory(action="next", current_date=date_str).pack()
        )
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def create_groups_keyboard(groups: List[ApiGroupDTO], columns: int = 2) -> InlineKeyboardMarkup:
    """
    Створює інлайн-клавіатуру зі списком груп у вигляді сітки.
    :param groups: Список об'єктів груп.
    :param columns: Кількість колонок у сітці (за замовчуванням 2).
    """
    buttons = []
    row = []
    for group in groups:
        btn = InlineKeyboardButton(
            text=group.name,
            callback_data=GroupCallbackFactory(id=group.id, name=group.name).pack()
        )
        row.append(btn)
        
        if len(row) == columns:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_regions_keyboard(regions: List[ApiRegionDTO], columns: int = 1) -> InlineKeyboardMarkup:
    """
    Створює інлайн-клавіатуру зі списком регіонів.
    """
    buttons = []
    row = []
    for region in regions:
        btn = InlineKeyboardButton(
            text=region.name,
            callback_data=RegionCallbackFactory(id=region.id).pack()
        )
        row.append(btn)
        
        if len(row) == columns:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)