from aiogram.fsm.state import State, StatesGroup

class RegistrationFSM(StatesGroup):
    choosing_group = State()
    choosing_region = State()

class SettingsFSM(StatesGroup):
    choosing_group = State()
    choosing_region = State()