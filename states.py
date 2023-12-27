from aiogram.filters.state import State, StatesGroup


class States(StatesGroup):
    after_restart = State()

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

    change_password = State()
    change_login = State()
    view_selected = State()