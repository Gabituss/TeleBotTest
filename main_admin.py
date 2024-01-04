import asyncio
import logging
import worksheet_updater

from aiogram_dialog import setup_dialogs, ShowMode
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.types import Message
from aiogram.types import Message, CallbackQuery, ErrorEvent
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState

from aiogram_dialog import DialogManager, StartMode

import windows_admin
from states_admin import States
from database import *
from config import *
from filters import SolverFilter

bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database("users.db")


@dp.message(SolverFilter(), Command("start"))
async def start(message: Message, state: FSMContext, dialog_manager: DialogManager):
    await state.update_data(user_id=message.chat.id)
    await dialog_manager.start(States.menu, mode=StartMode.RESET_STACK)


async def on_unknown_intent(event: ErrorEvent, state: FSMContext, dialog_manager: DialogManager):
    logging.error("Restarting dialog: %s", event.exception)
    await dialog_manager.start(
        States.menu, mode=StartMode.RESET_STACK, show_mode=ShowMode.SEND,
    )


async def main():
    dp.errors.register(on_unknown_intent, ExceptionTypeFilter(UnknownIntent))
    dp.include_router(windows_admin.dialog)
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename="admin.log", filemode="w")
    asyncio.run(main())
