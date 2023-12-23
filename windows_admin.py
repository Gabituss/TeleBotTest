from datetime import date

from aiogram.types import CallbackQuery

from aiogram import Dispatcher, Bot, F
from aiogram_dialog.widgets.kbd import *
from aiogram_dialog.widgets.text import *
from aiogram_dialog.widgets.input import *
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram.fsm.context import FSMContext

from states_admin import States
from random import randint
from typing import Any
from database import *

db = Database("users.db")


async def tests_data(state: FSMContext, **kwargs):
    tests = db.get_test_list()
    return {'tests': tests}


async def get_test_data(dialog_manager: DialogManager, **kwargs):
    return {
        "selected_type": str(db.get_test(dialog_manager.dialog_data["chosen_option"])),
    }


async def get_users_data(dialog_manager: DialogManager, **kwargs):
    users = db.get_users()
    return {'users': users}


async def on_click_user(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["chosen_user"] = int(item_id.split()[1])
    await manager.switch_to(States.user_tasks)


async def users_back(callback: CallbackQuery, widget: Any, manager: DialogManager):
    await manager.switch_to(States.users)


async def get_user_tasks(dialog_manager: DialogManager, **kwargs):
    tasks = db.get_tasks(dialog_manager.dialog_data["chosen_user"])
    print([task.type_id for task in tasks])
    tasks_types = [db.get_test(task.type_id).description for task in tasks]
    return {'tasks': zip(tasks_types, tasks)}


async def change_cost(event, widget, dialog_manager: DialogManager, *_):
    test_id = dialog_manager.dialog_data["chosen_option"]
    old_test = db.get_test(test_id)
    db.update_test(test_id,
                   Test(old_test.test_id, int(dialog_manager.find("newcost").get_value()), old_test.description))
    await dialog_manager.switch_to(States.change_option)


async def change_name(event, widget, dialog_manager: DialogManager, *_):
    test_id = dialog_manager.dialog_data["chosen_option"]
    old_test = db.get_test(test_id)
    db.update_test(test_id,
                   Test(old_test.test_id, old_test.cost, dialog_manager.find("newname").get_value()))
    await dialog_manager.switch_to(States.change_option)


async def delete_option(event, windget, dialog_manager: DialogManager, *_):
    test_id = dialog_manager.dialog_data["chosen_option"]
    db.remove_test(test_id)
    await dialog_manager.switch_to(States.menu)


async def add_name(event, widget, dialog_manager: DialogManager, *_):
    await dialog_manager.switch_to(States.add_option_name)


async def add_solver(event, widget, dialog_manager: DialogManager, *_):
    db.add_solver(Solver(int(dialog_manager.find("solverid").get_value())))
    await event.answer("OK")
    await dialog_manager.switch_to(States.menu)


async def remove_solver(event, widget, dialog_manager: DialogManager, *_):
    db.remove_solver(Solver(int(dialog_manager.find("solverid").get_value())))
    await event.answer("OK")
    await dialog_manager.switch_to(States.menu)


async def add_option(event, widget, dialog_manager: DialogManager, *_):
    test = Test(-1, int(dialog_manager.find("add_cost").get_value()), dialog_manager.find("add_name").get_value())
    db.add_test(test)
    await dialog_manager.switch_to(States.menu)


async def on_click(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    manager.dialog_data["chosen_option"] = int(item_id.split()[1])
    await manager.switch_to(States.change_option)


MAIN_MENU_BTN = SwitchTo(
    Const("Меню"),
    id="mainb",
    state=States.menu
)
dialog = Dialog(
    Window(
        Const("Админ меню"),
        SwitchTo(Const("Изменить доступные опции"), id="change", state=States.change_options),
        SwitchTo(Const("Добавить новую опцию"), id="add", state=States.add_option_cost),
        SwitchTo(Const("Менеджмент пользователей"), id="users", state=States.users),
        SwitchTo(Const("Добавить решалу"), id="solver", state=States.add_solver),
        SwitchTo(Const("Удалить решалу"), id="remove_solver", state=States.remove_solver),
        state=States.menu
    ),

    Window(
        Const("Tests"),
        ScrollingGroup(
            Select(
                Format("{item.description} - {item.cost}₽"),
                item_id_getter=lambda test: f"test {test.test_id}",
                items="tests",
                id="tests",
                on_click=on_click
            ),
            id="tests_group",
            width=1,
            height=6,
        ),
        MAIN_MENU_BTN,
        getter=tests_data,
        state=States.change_options
    ),
    Window(
        Jinja(
            "<b>Выбранная опция</b>: {{selected_type}}\n"
        ),
        SwitchTo(Const("Изменить цену"), state=States.change_cost, id="change_cost"),
        SwitchTo(Const("Изменить название"), state=States.change_name, id="change_name"),
        Button(Const("Удалить опцию"), on_click=delete_option, id="delete_option"),
        MAIN_MENU_BTN,
        getter=get_test_data,
        state=States.change_option,
        parse_mode="html",
    ),
    Window(
        Const("Введи новую цену"),
        TextInput(id="newcost", on_success=change_cost),
        state=States.change_cost,
    ),
    Window(
        Const("Введи новое название"),
        TextInput(id="newname", on_success=change_name),
        state=States.change_name
    ),
    Window(
        Const("Введи стоимость"),
        TextInput(id="add_cost", on_success=add_name),
        state=States.add_option_cost
    ),
    Window(
        Const("Введи название"),
        TextInput(id="add_name", on_success=add_option),
        state=States.add_option_name
    ),

    Window(
        Const("Пользователи"),
        ScrollingGroup(
            Select(
                Format("{item.name}"),
                item_id_getter=lambda user: f"user {user.id}",
                items="users",
                id="users",
                on_click=on_click_user
            ),
            id="users_group",
            width=1,
            height=10,
        ),
        MAIN_MENU_BTN,
        getter=get_users_data,
        state=States.users
    ),
    Window(
        Const("Заказы пользователя"),
        ScrollingGroup(
            Select(
                Format("{item[0]}: {item[1].as_str}"),
                item_id_getter=lambda task: f"task {task[1].task_id}",
                items="tasks",
                id="tasks",
            ),
            id="user_tasks_group",
            width=1,
            height=6,
        ),
        Button(Const("Назад"), on_click=users_back, id="users_back"),
        getter=get_user_tasks,
        state=States.user_tasks
    ),
    Window(
        Const("Введи id решалы"),
        TextInput(id="solverid", on_success=add_solver),
        state=States.add_solver
    ),
    Window(
        Const("Введи id решалы"),
        TextInput(id="solverid", on_success=remove_solver),
        state=States.remove_solver
    )
)
