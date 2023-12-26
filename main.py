import asyncio
import logging

from aiogram_dialog import setup_dialogs, ShowMode
from aiogram import Bot, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.types import Message, CallbackQuery, ErrorEvent
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState

from aiogram_dialog import DialogManager, StartMode

import windows
import worksheet_updater
from filters import SolverFilter
from database import *
from states import States
from config import *

bot = Bot(token=MAIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database(DB_PATH)
upd = worksheet_updater.Updater("telesolve.json", DB_PATH)


@dp.message(SolverFilter(), Command("update"))
async def update(message: Message, state: FSMContext, dialog_manager: DialogManager):
    upd.update_tasks_list()
    await message.answer("OK")


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext, dialog_manager: DialogManager):
    await state.update_data(user_id=message.chat.id)
    await dialog_manager.start(States.after_restart, mode=StartMode.RESET_STACK)


@dp.message(Command("menu"))
async def menu(message: Message, state: FSMContext, dialog_manager: DialogManager):
    await state.update_data(user_id=message.chat.id)
    await dialog_manager.start(States.after_restart, mode=StartMode.RESET_STACK)


@dp.message(SolverFilter(), Command("erase"))
async def erase(message: Message, state: FSMContext, dialog_manager: DialogManager):
    await message.answer("OK")


@dp.message(SolverFilter(), Command("start_task"))
async def start_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    db.update_task_mark(task_id, 0)

    await message.answer("OK")
    upd.update_tasks_list()


@dp.message(SolverFilter(), Command("finish_task"))
async def finish_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    mark = int(message.text.split()[2])
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)

    db.update_task_mark(task_id, mark)

    await message.bot.send_message(task.user_id,
                                   f"Заказ \"{test.description}: {task.test_name}\" c id={task.task_id} выполнен, получена оценка \"{mark}\" ✨")
    await message.answer("OK")
    upd.update_tasks_list()


@dp.message(SolverFilter(), Command("write"))
async def write_to_user(message: Message, state: FSMContext, dialog_manager: DialogManager):
    user_id = int(message.text.split()[1])
    task_id = int(message.text.split()[2])
    text = " ".join(message.text.split()[3:])

    task = db.get_task(task_id)
    await message.bot.send_message(user_id, f"Сообщение по поводу заказа \"{task.test_name}\" с id={task_id}:\n{text}")
    await message.answer("OK")


@dp.callback_query(F.data.startswith("approve"))
async def approve_task(callback: CallbackQuery):
    task_id = int(callback.data.split()[1])
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)

    db.update_task_approve_status(task_id, 3)

    await callback.message.bot.send_message(task.user_id, text=f"Заказ \"{test.description}\" c id={task.task_id} подтвержден ✅")
    await callback.message.bot.send_document(
        chat_id=callback.message.chat.id,
        document=callback.message.document.file_id,
        caption=f"Заказ от {task.user_name} \"{test.description}\" c id={task.task_id} подтвержден"
    )

    tasks = db.get_all_tasks()
    cnt = 0
    for tsk in tasks:
        cnt += tsk.approved != 2

    if cnt % 5 == 0:
        upd.update_tasks_list()


@dp.callback_query(F.data.startswith("decline"))
async def decline_task(callback: CallbackQuery):
    task_id = int(callback.data.split()[1])
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)
    db.update_task_approve_status(task_id, 1)

    await callback.bot.send_message(task.user_id,
                                    f"Заказ {task.test_name}\" c id={task.task_id} отклонен ❌, обратитесь к менеджеру чтобы узнать причину")
    await callback.message.bot.send_document(
        chat_id=callback.message.chat.id,
        document=callback.message.document.file_id,
        caption=f"Заказ от {task.user_name} \"{test.description}\" c id={task.task_id} отклонен"
    )
    await callback.message.delete()

    tasks = db.get_all_tasks()
    cnt = 0
    for tsk in tasks:
        cnt += tsk.approved != 2

    if cnt % 5 == 0:
        upd.update_tasks_list()


async def on_unknown_intent(event: ErrorEvent, state: FSMContext, dialog_manager: DialogManager):
    logging.error("Restarting dialog: %s", event.exception)
    await dialog_manager.start(
        States.after_restart, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND,
    )


async def main():
    dp.errors.register(on_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.include_router(windows.dialog)
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
