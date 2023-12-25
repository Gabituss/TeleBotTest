from datetime import datetime, time, date

from functools import cmp_to_key

import aiogram.types.message
from aiogram.types import CallbackQuery

from config import *
from aiogram import Dispatcher, Bot, F
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ContentType, Message
from aiogram_dialog.widgets.kbd import *
from aiogram_dialog.widgets.text import *
from aiogram_dialog.widgets.input import *
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram.fsm.context import FSMContext
from aiogram_dialog import DialogManager, StartMode, ShowMode

from states import States
from random import randint
from typing import Any
from database import *
from worksheet_updater import Updater

db = Database("users.db")
upd = Updater("telesolve.json", "users.db")

MAIN_MENU_BTN = SwitchTo(Const("Меню"), id="mainb", state=States.main_menu)
CANCEL_EDIT = SwitchTo(Const("Отменить редактирование"), when=F["dialog_data"]["finished"], id="cnl_edt",
                       state=States.preview, )


def compare(a: Task, b: Task):
    if a == b:
        return 0
    if a.approved > b.approved:
        return -1
    if a.approved < b.approved:
        return 1
    if a.mark > 0 and b.mark > 0:
        return -1 if a.task_id < b.task_id else 1
    if a.mark > 0 >= b.mark:
        return 1
    if a.mark <= 0 < b.mark:
        return -1
    if a.mark == 0 and b.mark == -1:
        return 1
    if a.mark == -1 and b.mark == 0:
        return -1

    date1 = datetime.strptime(a.deadline, '%Y-%m-%d %H:%M')
    date2 = datetime.strptime(b.deadline, '%Y-%m-%d %H:%M')
    return -1 if date1 < date2 else 1


async def get_user_tasks(state: FSMContext, dialog_manager: DialogManager, **kwargs):
    tasks = db.get_tasks(dialog_manager.dialog_data["user_id"])
    tasks.sort(key=cmp_to_key(compare))
    return {'tasks': tasks}


async def get_tests_data(state: FSMContext, dialog_manager: DialogManager, **kwargs):
    tests = db.get_test_list()
    return {'tests': tests}


def check_time(tm):
    try:
        time.fromisoformat(tm)
        return True
    except ValueError:
        return False


async def get_order_data(dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data["finished"] = True
    deadline: date = dialog_manager.dialog_data["date"]

    data = dict()
    data["selected_type"] = str(db.get_test(dialog_manager.dialog_data["chosen_option"]))
    data["name"] = dialog_manager.find("write_name").get_value()
    data["description"] = db.get_test(dialog_manager.dialog_data["chosen_option"]).description
    tm = dialog_manager.find("write_deadline_time").get_value()
    if len(tm.split(":")[0]) < 2:
        tm = "0" + tm

    if check_time(tm):
        data["date"] = deadline.strftime('%Y-%m-%d') + " " + dialog_manager.find("write_deadline_time").get_value()
        dialog_manager.dialog_data["correct"] = True
    else:
        data["date"] = "Исправьте время дедлайна ❌"
        dialog_manager.dialog_data["correct"] = False

    data["cost"] = db.get_test(dialog_manager.dialog_data["chosen_option"]).cost

    return data


async def on_option_selected(callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    now = datetime.now().time()
    start, end = db.get_time_deltas()

    if start <= now <= end:
        manager.dialog_data["chosen_option"] = int(item_id.split()[1])
        await manager.switch_to(States.write_name)
    else:
        await manager.close_manager()
        await manager.start(States.after_restart)
        await callback.message.answer("Мы сейчас не принимаем заказы 🙁, введите /menu")
        await manager.switch_to(States.after_restart)


async def on_date_click(callback: CallbackQuery, widget, dialog_manager: DialogManager, selected_date: date):
    dialog_manager.dialog_data["date"] = selected_date
    if selected_date >= date.today():
        await next_or_end(0, 0, dialog_manager)


async def next_or_end(event, widget, dialog_manager: DialogManager, *_):
    if dialog_manager.dialog_data.get("finished"):
        await dialog_manager.switch_to(States.preview)
    else:
        await dialog_manager.next()


async def confirm_purchase(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data["finished"] = False
    data = await get_order_data(dialog_manager)
    dialog_manager.dialog_data["id"] = gen_id()

    if not db.user_exists(callback.message.chat.id):
        db.add_user(User(callback.message.chat.id, data["name"]))

    await dialog_manager.switch_to(States.pay)


async def write_login(message: Message, widget, dialog_manager: DialogManager, *_):
    await dialog_manager.switch_to(States.write_password)


async def add_task(message: Message, widget, dialog_manager: DialogManager, *_):
    data = await get_order_data(dialog_manager)
    db.add_task(Task(
        type_id=dialog_manager.dialog_data["chosen_option"],
        task_id=dialog_manager.dialog_data["id"],
        user_id=message.chat.id,
        test_name=db.get_test(dialog_manager.dialog_data["chosen_option"]).description,
        login_data=dialog_manager.find("write_login").get_value() + " " + dialog_manager.find(
            "write_password").get_value(),
        deadline=data["date"],
        mark=-1,
        user_name=data["name"],
        approved=2
    ))

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="Подтвердить", callback_data=f"approve {dialog_manager.dialog_data['id']}"))
    builder.add(
        types.InlineKeyboardButton(text="Отклонить", callback_data=f"decline {dialog_manager.dialog_data['id']}"))
    await message.bot.send_document(MANAGER_ID, dialog_manager.dialog_data["file_id"], caption=
    f"Заказ от {data['name']} \"{data['description']}\" за {data['cost']}₽\n", reply_markup=builder.as_markup())

    await message.answer("❤Благодарим Вас за покупку❤️\n\n✍🏼Тест будет выполнен до конца дедлайна✍🏼")
    await dialog_manager.switch_to(States.main_menu)

    if len(db.get_all_tasks()) % 5 == 0:
        upd.update_tasks_list()


async def receipt_handler(message: Message, message_input: MessageInput, manager: DialogManager):
    data = await get_order_data(manager)
    manager.dialog_data["file_id"] = message.document.file_id
    await manager.switch_to(States.write_login)


async def decline_purchase(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data["finished"] = False
    await dialog_manager.switch_to(States.main_menu)


async def go_to_menu(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data["user_id"] = callback.message.chat.id


async def open_menu(callback: CallbackQuery, widget: Any, manager: DialogManager):
    now = datetime.now().time()
    start, end = db.get_time_deltas()

    if start <= now <= end:
        await manager.switch_to(States.buy_menu)
    else:
        await callback.message.answer("Мы сейчас не принимаем заказы 🙁, введите /menu")
        await manager.switch_to(States.after_restart)

dialog = Dialog(
    Window(
        Const("Нажмите на кнопку чтобы перейти в меню"),
        SwitchTo(Const("Меню"), id="menu", on_click=go_to_menu, state=States.main_menu),
        state=States.after_restart
    ),

    Window(
        Const("Меню"),
        Button(Const("💎 Заказать тест 💎"), id="buy", on_click=open_menu),
        SwitchTo(Const("⏳ Мои заказы ⏳"), id="tasks", state=States.tasks_menu),
        Url(Const("✏️ Менеджер ✏️"), Const('https://t.me/MANAGER_MTTS')),
        Url(Const("📕️ Канал 📕️"), Const('https://t.me/MGMSU_TestTech_Squad')),
        state=States.main_menu
    ),
    Window(
        Const("Здесь Вы можете выбрать тест, который нужно решить 📝\n"
              "В случае если вашего теста нет в списке - напишите менеджеру для его добавления 🔎"),
        ScrollingGroup(
            Select(
                Format("{item.description} - {item.cost}₽"),
                item_id_getter=lambda test: f"test {test.test_id}",
                items="tests",
                id="tests",
                on_click=on_option_selected
            ),
            id="tests_group",
            width=1,
            height=10,
        ),
        MAIN_MENU_BTN,
        CANCEL_EDIT,
        getter=get_tests_data,
        state=States.buy_menu,
    ),
    Window(
        Const("Здесь Вы можете ознакомиться с Вашими заказами 🗒"),
        ScrollingGroup(
            Select(
                Format("{item.as_str}"),
                item_id_getter=lambda task: f"task {task.task_id}",
                items="tasks",
                id="tasks",
            ),
            id="tasks_group",
            width=1,
            height=6,
        ),
        MAIN_MENU_BTN,
        getter=get_user_tasks,
        state=States.tasks_menu
    ),
    Window(
        Const("Введите ФИО"),
        TextInput(id="write_name", on_success=next_or_end),
        CANCEL_EDIT,
        state=States.write_name
    ),
    Window(
        Const("Выберите дату дедлайна"),
        Calendar(id="write_deadline", on_click=on_date_click),
        CANCEL_EDIT,
        state=States.write_deadline
    ),
    Window(
        Const("Введите время дедлайна в формате час:минута, например \"16:30\" или \"09:30\" (МСК)"),
        TextInput(id="write_deadline_time", on_success=next_or_end),
        CANCEL_EDIT,
        state=States.write_deadline_time
    ),
    Window(
        Jinja(
            "Пожалуйста, Проверьте введенные данные\n"
            "<b>Выбранная опция</b>: {{selected_type}}\n"
            "<b>Фио</b>: {{name}}\n"
            "<b>Дедлайн</b>: {{date}}\n"
        ),
        SwitchTo(Const("Изменить опцию"), state=States.buy_menu, id="to_buy_menu"),
        SwitchTo(Const("Изменить ФИО"), state=States.write_name, id="to_name"),
        SwitchTo(Const("Изменить дату дедлайна"), state=States.write_deadline, id="to_deadline"),
        SwitchTo(Const("Изменить время дедлайна"), state=States.write_deadline_time, id="to_deadline_time"),
        Button(Const("Оплатить ✅"), on_click=confirm_purchase, id="confirm_purchase", when=F["dialog_data"]["correct"]),
        Button(Const("Отмена ❌"), on_click=decline_purchase, id="decline_purchase"),
        getter=get_order_data,
        state=States.preview,
        parse_mode="html",
    ),
    Window(
        Jinja(
            "К оплате <b>{{cost}}₽</b>\n"
            "🧾 Переведите деньги на **** и <b>отправьте файлом</b> чек об оплате 🧾\n\n"
            "👩🏻‍💼 Заказ будет ждать подтвердения менеджера 👩🏻‍💼\n\n"
            "🔔 Как только он будет подтвержден, Вам прийдет уведомление 🔔\n\n"
            "⌛️ Если в течение n часов не будет подтверждения, обратитесь к <a href=\"https://t.me/MANAGER_MTTS\">менеджеру</a> ⌛️"
        ),
        MessageInput(receipt_handler, content_types=[ContentType.DOCUMENT]),
        getter=get_order_data,
        state=States.pay,
        parse_mode="html",
    ),
    Window(
        Const("Введите логин 👨‍💻"),
        TextInput(id="write_login", on_success=write_login),
        state=States.write_login
    ),
    Window(
        Const("Введите пароль 🔑"),
        TextInput(id="write_password", on_success=add_task),
        state=States.write_password
    )
)
