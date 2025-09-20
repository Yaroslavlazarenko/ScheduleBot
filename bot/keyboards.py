from typing import List
from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, 
                           KeyboardButton, ReplyKeyboardMarkup)

from api import ApiGroupDTO, ApiRegionDTO, ApiTeacherDTO

class GroupCallbackFactory(CallbackData, prefix="group"):
    id: int
    name: str

class RegionCallbackFactory(CallbackData, prefix="region"):
    id: int

class ScheduleCallbackFactory(CallbackData, prefix="schedule"):
    action: str
    current_date: str
    original_user_id: int 

class TeacherCallbackFactory(CallbackData, prefix="teacher"):
    action: str
    id: int | None = None 

def create_main_keyboard() -> ReplyKeyboardMarkup:
    """Створює головну клавіатуру з основними діями."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🗓 Отримати розклад"), 
                KeyboardButton(text="👨‍🏫 Вчителі")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def create_schedule_navigation_keyboard(current_date: date, original_user_id: int) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для навігації по днях розкладу та його закриття."""
    date_str = current_date.isoformat()
    
    navigation_buttons = [
        InlineKeyboardButton(
            text="⬅️",
            callback_data=ScheduleCallbackFactory(
                action="prev", 
                current_date=date_str, 
                original_user_id=original_user_id
            ).pack()
        ),
        InlineKeyboardButton(
            text="➡️",
            callback_data=ScheduleCallbackFactory(
                action="next", 
                current_date=date_str, 
                original_user_id=original_user_id
            ).pack()
        )
    ]
    
    close_button = InlineKeyboardButton(
        text="Закрити ❌",
        callback_data=ScheduleCallbackFactory(
            action="close",
            current_date=date_str,
            original_user_id=original_user_id
        ).pack()
    )
    
    keyboard = [
        navigation_buttons,
        [close_button]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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

def create_teachers_keyboard(teachers: List[ApiTeacherDTO], columns: int = 2) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру зі списком викладачів."""
    buttons = []
    row = []
    for teacher in sorted(teachers, key=lambda t: t.last_name):
        parts = [teacher.last_name]
        if teacher.first_name:
            parts.append(f"{teacher.first_name[0].upper()}.")
        if teacher.middle_name:
            parts.append(f"{teacher.middle_name[0].upper()}.")
        
        abbreviated_name = " ".join(parts)
        
        btn = InlineKeyboardButton(
            text=abbreviated_name,
            callback_data=TeacherCallbackFactory(action="select", id=teacher.id).pack()
        )
        row.append(btn)
        
        if len(row) == columns:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)

    close_button = InlineKeyboardButton(
        text="Закрити ❌",
        callback_data=TeacherCallbackFactory(action="close").pack()
    )
    buttons.append([close_button])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_teacher_details_keyboard() -> InlineKeyboardMarkup:
    """Створює клавіатуру з кнопкою "Назад" до списку викладачів."""
    button = InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=TeacherCallbackFactory(action="back").pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])