from aiogram.fsm.state import State, StatesGroup

class RegistrationFSM(StatesGroup):
    choosing_group = State()
    choosing_region = State()

class SettingsFSM(StatesGroup):
    choosing_group = State()
    choosing_region = State()

class AdminFSM(StatesGroup):
    waiting_for_json = State()
    choosing_group_for_calendar = State() # <-- Додано новий стан

class BroadcastFSM(StatesGroup):
    choosing_type = State()
    getting_schedule_time = State()
    getting_message = State()
    confirming_broadcast = State()