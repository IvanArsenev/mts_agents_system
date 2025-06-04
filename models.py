from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    waiting_for_name = State()
    waiting_for_birth_date = State()
    waiting_for_number = State()
