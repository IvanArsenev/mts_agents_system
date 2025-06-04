"""Models for telegram bot and backend project."""

from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):  # pylint: disable=too-few-public-methods
    """Model for steps of form."""
    waiting_for_name = State()
    waiting_for_birth_date = State()
    waiting_for_number = State()
