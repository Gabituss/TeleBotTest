from aiogram.filters.state import State, StatesGroup


class States(StatesGroup):
    menu = State()
    change_options = State()
    change_option = State()
    change_cost = State()
    change_name = State()
    add_option_cost = State()
    add_option_name = State()
    users = State()
    user_tasks = State()
    add_solver = State()
    remove_solver = State()