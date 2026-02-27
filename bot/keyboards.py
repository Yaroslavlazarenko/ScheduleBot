from datetime import date
from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# ==========================================
# Фабрики Callback Data (для обробки натискань)
# ==========================================

class BroadcastCallbackFactory(CallbackData, prefix="broadcast"):
    action: str
class GroupCallbackFactory(CallbackData, prefix="group"):
    id: int
    name: str
class RegionCallbackFactory(CallbackData, prefix="region"):
    id: int
class TeacherCallbackFactory(CallbackData, prefix="teacher"):
    action: str
    id: int | None = None 
class SettingsCallbackFactory(CallbackData, prefix="settings"):
    action: str
class SubjectCallbackFactory(CallbackData, prefix="subject"):
    action: str
    subject_name_id: int | None = None

class ScheduleCallbackFactory(CallbackData, prefix="schedule"):
    action: str
    schedule_type: str
    current_date: str
    group_id: int 


# ==========================================
# Головні клавіатури та меню
# ==========================================

def create_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = [[KeyboardButton(text="🗓 Отримати розклад"), KeyboardButton(text="🗓 Розклад на тиждень")],
          [KeyboardButton(text="👨‍🏫 Вчителі"), KeyboardButton(text="📚 Предмети")],
          [KeyboardButton(text="⚙️ Налаштування")]]
    if is_admin: kb.append([KeyboardButton(text="👑 Адмін-панель")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def create_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Змінити групу", callback_data=SettingsCallbackFactory(action="change_group").pack())],
        [InlineKeyboardButton(text="🌍 Змінити часовий пояс", callback_data=SettingsCallbackFactory(action="change_region").pack())],
        [InlineKeyboardButton(text="Закрити ❌", callback_data=SettingsCallbackFactory(action="close").pack())]
    ])

# ==========================================
# Адмін-панель та розсилка
# ==========================================

def create_admin_panel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✉️ Створити розсилку", callback_data="start_broadcast")],
        [InlineKeyboardButton(text="🔄 Оновити базу (JSON)", callback_data="upload_json")], # НОВА КНОПКА
        [InlineKeyboardButton(text="Закрити ❌", callback_data="close_admin_panel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Скасувати", callback_data=BroadcastCallbackFactory(action="cancel").pack())]])


def create_broadcast_confirmation_keyboard(is_scheduled: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Надіслати всім", callback_data=BroadcastCallbackFactory(action="send").pack())],
        [InlineKeyboardButton(text="✏️ Редагувати текст", callback_data=BroadcastCallbackFactory(action="edit_text").pack())],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data=BroadcastCallbackFactory(action="cancel").pack())]
    ])

# ==========================================
# Навігація розкладом
# ==========================================

def create_schedule_navigation_keyboard(current_date: date, group_id: int) -> InlineKeyboardMarkup:
    date_str = current_date.isoformat()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️", callback_data=ScheduleCallbackFactory(action="prev", schedule_type="day", current_date=date_str, group_id=group_id).pack()),
         InlineKeyboardButton(text="➡️", callback_data=ScheduleCallbackFactory(action="next", schedule_type="day", current_date=date_str, group_id=group_id).pack())],
        [InlineKeyboardButton(text="Закрити ❌", callback_data=ScheduleCallbackFactory(action="close", schedule_type="day", current_date=date_str, group_id=group_id).pack())]
    ])

def create_weekly_schedule_navigation_keyboard(current_date: date, group_id: int) -> InlineKeyboardMarkup:
    date_str = current_date.isoformat()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Попер. тиж.", callback_data=ScheduleCallbackFactory(action="prev_week", schedule_type="week", current_date=date_str, group_id=group_id).pack()),
         InlineKeyboardButton(text="Наст. тиж. ➡️", callback_data=ScheduleCallbackFactory(action="next_week", schedule_type="week", current_date=date_str, group_id=group_id).pack())],
        [InlineKeyboardButton(text="Закрити ❌", callback_data=ScheduleCallbackFactory(action="close", schedule_type="week", current_date=date_str, group_id=group_id).pack())]
    ])

def create_show_schedule_keyboard(group_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗓 Розгорнути розклад", callback_data=ScheduleCallbackFactory(action="show", schedule_type="day", current_date=date.today().isoformat(), group_id=group_id).pack())]])

def create_show_weekly_schedule_keyboard(group_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗓 Розгорнути розклад на тиждень", callback_data=ScheduleCallbackFactory(action="show", schedule_type="week", current_date=date.today().isoformat(), group_id=group_id).pack())]])


# ==========================================
# Динамічні клавіатури з db.json (Групи, Регіони, Викладачі, Предмети)
# ==========================================

def create_groups_keyboard(groups: list[dict], columns: int = 2, add_back_button: bool = False) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for g in groups:
        row.append(InlineKeyboardButton(text=g["name"], callback_data=GroupCallbackFactory(id=g["group_id"], name=g["name"]).pack()))
        if len(row) == columns: buttons.append(row); row = []
    if row: buttons.append(row)
    if add_back_button: buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=SettingsCallbackFactory(action="back_to_menu").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_regions_keyboard(regions: list[dict], columns: int = 1, add_back_button: bool = False) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for r in regions:
        row.append(InlineKeyboardButton(text=r["name"], callback_data=RegionCallbackFactory(id=r["region_id"]).pack()))
        if len(row) == columns: buttons.append(row); row = []
    if row: buttons.append(row)
    if add_back_button: buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=SettingsCallbackFactory(action="back_to_menu").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_teachers_keyboard(teachers: list[dict], columns: int = 2) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for t in sorted(teachers, key=lambda x: x["name"]):
        row.append(InlineKeyboardButton(text=f"{t['title']} {t['name']}", callback_data=TeacherCallbackFactory(action="select", id=t["teacher_id"]).pack()))
        if len(row) == columns: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Закрити ❌", callback_data=TeacherCallbackFactory(action="close").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_teacher_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=TeacherCallbackFactory(action="back").pack())]])


def create_subjects_keyboard(subjects: list[dict], columns: int = 2) -> InlineKeyboardMarkup:
    buttons, row = [], []
    for s in sorted(subjects, key=lambda x: x["full_name"]):
        row.append(InlineKeyboardButton(text=s["abbreviation"], callback_data=SubjectCallbackFactory(action="select", subject_name_id=s["subject_id"]).pack()))
        if len(row) == columns: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="Закрити ❌", callback_data=SubjectCallbackFactory(action="close").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_subject_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=SubjectCallbackFactory(action="back").pack())]])


