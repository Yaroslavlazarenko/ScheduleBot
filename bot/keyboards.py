from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from api import ApiGroupDTO, ApiRegionDTO

class GroupCallbackFactory(CallbackData, prefix="group"):
    id: int
    name: str

class RegionCallbackFactory(CallbackData, prefix="region"):
    id: int
    number: int

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

def create_regions_keyboard(regions: List[ApiRegionDTO], columns: int = 3) -> InlineKeyboardMarkup:
    """
    Створює інлайн-клавіатуру зі списком регіонів у вигляді сітки.
    :param regions: Список об'єктів регіонів.
    :param columns: Кількість колонок у сітці (за замовчуванням 3, оскільки номери коротші).
    """
    buttons = []
    row = []
    for region in regions:
        btn = InlineKeyboardButton(
            text=str(region.number),
            callback_data=RegionCallbackFactory(id=region.id, number=region.number).pack()
        )
        row.append(btn)
        
        if len(row) == columns:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)