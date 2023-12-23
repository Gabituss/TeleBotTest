from aiogram.filters.state import State, StatesGroup


class States(StatesGroup):
    main_menu = State()
    tasks_menu = State()
    buy_menu = State()

    write_name = State()
    write_description = State()
    write_deadline = State()
    write_deadline_time = State()
    write_login = State()
    write_password = State()
    preview = State()
    pay = State()