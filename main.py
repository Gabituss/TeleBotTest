import asyncio
import logging

from aiogram_dialog import setup_dialogs
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import Message

from aiogram_dialog import DialogManager, StartMode

import windows
import worksheet_updater
from filters import SolverFilter
from database import *
from states import States

bot = Bot(token="6723741437:AAGGC1kf2TUcEAgMRvxkSo98-hs-BqexBAQ")
dp = Dispatcher(storage=MemoryStorage())
db = Database("users.db")
upd = worksheet_updater.Updater("telesolve.json", "users.db")


@dp.message(Command("start"))
async def start(message: Message, state: FSMContext, dialog_manager: DialogManager):
    await state.update_data(user_id=message.chat.id)
    await dialog_manager.start(States.main_menu, mode=StartMode.RESET_STACK)


@dp.message(SolverFilter(), Command("update"))
async def update(message: Message, state: FSMContext, dialog_manager: DialogManager):
    upd.clear()
    upd.update_tasks_list()
    await message.answer("OK")


@dp.message(SolverFilter(), Command("erase"))
async def erase(message: Message, state: FSMContext, dialog_manager: DialogManager):
    upd.clear()
    await message.answer("OK")


@dp.message(SolverFilter(), Command("start_task"))
async def start_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    cell = message.text.split()[2]
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)

    db.update_task_mark(task_id, 0)

    upd.clear()
    upd.update_tasks_list()

    # await message.bot.send_message(task.user_id, f"Заказ \"{test.description}: {task.test_name}\" принят в работу")
    await message.answer("OK")


@dp.message(SolverFilter(), Command("finish_task"))
async def finish_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    cell = message.text.split()[2]
    mark = int(message.text.split()[3])
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)

    db.update_task_mark(task_id, mark)

    upd.clear()
    upd.update_tasks_list()

    await message.bot.send_message(task.user_id,
                                   f"Заказ \"{test.description}: {task.test_name}\" выполнен, получена оценка \"{mark}\"")
    await message.answer("OK")


@dp.message(SolverFilter(), Command("approve"))
async def approve_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)

    db.update_task_approve_status(task_id, 3)

    upd.clear()
    upd.update_tasks_list()

    await message.bot.send_message(task.user_id, text=
    f"Заказ \"{test.description}\" подтвержден")
    await message.answer("OK")


@dp.message(SolverFilter(), Command("decline"))
async def decline_task(message: Message, state: FSMContext, dialog_manager: DialogManager):
    task_id = int(message.text.split()[1])
    reason = message.text.split()[2]
    task = db.get_task(task_id)
    test = db.get_test(task.type_id)
    db.update_task_approve_status(task_id, 1)

    upd.clear()
    upd.update_tasks_list()

    await message.bot.send_message(task.user_id,
                                   f"Заказ \"{test.description}: {task.test_name}\" отклонен по причине: " + reason)
    await message.answer("OK")


async def main():
    dp.include_router(windows.dialog)
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
