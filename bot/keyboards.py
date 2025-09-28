from typing import List
from datetime import date
from datetime import timedelta

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, 
                           KeyboardButton, ReplyKeyboardMarkup)

from api import ApiGroupDTO, ApiRegionDTO, ApiTeacherDTO, ApiGroupedSubjectDTO

class BroadcastCallbackFactory(CallbackData, prefix="broadcast"):
    action: str

class GroupCallbackFactory(CallbackData, prefix="group"):
    id: int
    name: str

class RegionCallbackFactory(CallbackData, prefix="region"):
    id: int

class ScheduleCallbackFactory(CallbackData, prefix="schedule"):
    action: str
    schedule_type: str
    current_date: str
    original_user_id: int 

class TeacherCallbackFactory(CallbackData, prefix="teacher"):
    action: str
    id: int | None = None 

class SettingsCallbackFactory(CallbackData, prefix="settings"):
    action: str

class SubjectCallbackFactory(CallbackData, prefix="subject"):
    action: str
    subject_name_id: int | None = None

def create_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Створює головну клавіатуру з основними діями."""
    keyboard_layout = [
        [
            KeyboardButton(text="🗓 Отримати розклад"),
            KeyboardButton(text="🗓 Розклад на тиждень")
        ],
        [
            KeyboardButton(text="👨‍🏫 Вчителі"), 
            KeyboardButton(text="📚 Предмети")
        ],
        [
            KeyboardButton(text="⚙️ Налаштування")
        ]
    ]
    if is_admin:
        keyboard_layout.append([KeyboardButton(text="👑 Адмін-панель")])

    return ReplyKeyboardMarkup(
        keyboard=keyboard_layout,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def create_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для адмін-панелі."""
    buttons = [
        [InlineKeyboardButton(text="✉️ Створити розсилку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="Закрити ❌", callback_data="close_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_broadcast_type_keyboard() -> InlineKeyboardMarkup:
    """Створює клавіатуру для вибору типу розсилки."""
    buttons = [
        [
            InlineKeyboardButton(text="🚀 Відправити зараз", callback_data=BroadcastCallbackFactory(action="send_now").pack()),
            InlineKeyboardButton(text="🕒 Запланувати", callback_data=BroadcastCallbackFactory(action="schedule").pack())
        ],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=BroadcastCallbackFactory(action="cancel").pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_broadcast_confirmation_keyboard(is_scheduled: bool) -> InlineKeyboardMarkup:
    """Створює клавіатуру для підтвердження розсилки."""
    edit_buttons = [InlineKeyboardButton(text="✏️ Редагувати текст", callback_data=BroadcastCallbackFactory(action="edit_text").pack())]
    if is_scheduled:
        edit_buttons.append(InlineKeyboardButton(text="🕒 Редагувати час", callback_data=BroadcastCallbackFactory(action="edit_time").pack()))

    buttons = [
        [InlineKeyboardButton(text="✅ Підтвердити та створити", callback_data=BroadcastCallbackFactory(action="send").pack())],
        edit_buttons,
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=BroadcastCallbackFactory(action="cancel").pack())]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    """Створює клавіатуру з єдиною кнопкою "Скасувати"."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Скасувати", callback_data=BroadcastCallbackFactory(action="cancel").pack())
    ]])

def create_settings_keyboard() -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для меню налаштувань."""
    buttons = [
        [
            InlineKeyboardButton(
                text="Змінити групу",
                callback_data=SettingsCallbackFactory(action="change_group").pack()
            )
        ],
        [
            InlineKeyboardButton(
                text="Змінити часовий пояс",
                callback_data=SettingsCallbackFactory(action="change_region").pack()
            )
        ],
        [
             InlineKeyboardButton(
                text="Закрити ❌",
                callback_data=SettingsCallbackFactory(action="close").pack()
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_schedule_navigation_keyboard(
    current_date: date, 
    original_user_id: int,
    semester_start: date | None = None,
    semester_end: date | None = None
) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для навігації по днях розкладу."""
    date_str = current_date.isoformat()
    
    navigation_buttons = []

    if semester_start is None or current_date > semester_start:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=ScheduleCallbackFactory(
                    action="prev", schedule_type="day",
                    current_date=date_str, 
                    original_user_id=original_user_id
                ).pack()
            )
        )

    if semester_end is None or current_date < semester_end:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=ScheduleCallbackFactory(
                    action="next", schedule_type="day",
                    current_date=date_str, 
                    original_user_id=original_user_id
                ).pack()
            )
        )
    
    close_button = InlineKeyboardButton(
        text="Закрити ❌",
        callback_data=ScheduleCallbackFactory(
            action="close", schedule_type="day",
            current_date=date_str,
            original_user_id=original_user_id
        ).pack()
    )
    
    keyboard = []
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    keyboard.append([close_button])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_weekly_schedule_navigation_keyboard(
    current_date: date, 
    original_user_id: int,
    semester_start: date | None = None,
    semester_end: date | None = None
) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру для навігації по тижнях розкладу."""
    date_str = current_date.isoformat()
    
    navigation_buttons = []
    
    prev_week_date = current_date - timedelta(days=7)
    if semester_start is None or prev_week_date >= semester_start:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Попер. тиждень",
                callback_data=ScheduleCallbackFactory(
                    action="prev_week", schedule_type="week",
                    current_date=date_str, 
                    original_user_id=original_user_id
                ).pack()
            )
        )

    next_week_date = current_date + timedelta(days=7)
    if semester_end is None or next_week_date <= semester_end:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Наст. тиждень ➡️",
                callback_data=ScheduleCallbackFactory(
                    action="next_week", schedule_type="week",
                    current_date=date_str, 
                    original_user_id=original_user_id
                ).pack()
            )
        )
    
    close_button = InlineKeyboardButton(
        text="Закрити ❌",
        callback_data=ScheduleCallbackFactory(
            action="close", schedule_type="week",
            current_date=date_str,
            original_user_id=original_user_id
        ).pack()
    )
    
    keyboard = []
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    keyboard.append([close_button])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_show_schedule_keyboard(original_user_id: int) -> InlineKeyboardMarkup:
    """Створює клавіатуру з кнопкою для показу розкладу на сьогодні."""
    button = InlineKeyboardButton(
        text="🗓 Отримати розклад",
        callback_data=ScheduleCallbackFactory(
            action="show", schedule_type="day",
            current_date=date.today().isoformat(),
            original_user_id=original_user_id
        ).pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])

def create_show_weekly_schedule_keyboard(original_user_id: int) -> InlineKeyboardMarkup:
    """Створює клавіатуру з кнопкою для показу розкладу на тиждень."""
    button = InlineKeyboardButton(
        text="🗓 Отримати розклад на тиждень",
        callback_data=ScheduleCallbackFactory(
            action="show", schedule_type="week",
            current_date=date.today().isoformat(),
            original_user_id=original_user_id
        ).pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])

def create_groups_keyboard(groups: List[ApiGroupDTO], columns: int = 2, add_back_button: bool = False) -> InlineKeyboardMarkup:
    """
    Створює інлайн-клавіатуру зі списком груп у вигляді сітки.
    :param groups: Список об'єктів груп.
    :param columns: Кількість колонок у сітці (за замовчуванням 2).
    :param add_back_button: Додає кнопку "Назад" до меню налаштувань.
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

    if add_back_button:
        back_button = InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=SettingsCallbackFactory(action="back_to_menu").pack()
        )
        buttons.append([back_button])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_regions_keyboard(regions: List[ApiRegionDTO], columns: int = 1, add_back_button: bool = False) -> InlineKeyboardMarkup:
    """
    Створює інлайн-клавіатуру зі списком регіонів.
    :param add_back_button: Додає кнопку "Назад" до меню налаштувань.
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

    if add_back_button:
        back_button = InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=SettingsCallbackFactory(action="back_to_menu").pack()
        )
        buttons.append([back_button])
        
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

def create_subjects_keyboard(subjects: List[ApiGroupedSubjectDTO], columns: int = 2) -> InlineKeyboardMarkup:
    """Створює інлайн-клавіатуру зі списком предметів."""
    buttons = []
    row = []
    for subject in sorted(subjects, key=lambda s: s.name):
        btn = InlineKeyboardButton(
            text=subject.abbreviation,
            callback_data=SubjectCallbackFactory(action="select", subject_name_id=subject.subject_name_id).pack()
        )
        row.append(btn)
        
        if len(row) == columns:
            buttons.append(row)
            row = []
            
    if row:
        buttons.append(row)

    close_button = InlineKeyboardButton(
        text="Закрити ❌",
        callback_data=SubjectCallbackFactory(action="close").pack()
    )
    buttons.append([close_button])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_subject_details_keyboard() -> InlineKeyboardMarkup:
    """Створює клавіатуру з кнопкою "Назад" до списку предметів."""
    button = InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=SubjectCallbackFactory(action="back").pack()
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])