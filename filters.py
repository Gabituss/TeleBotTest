from aiogram.filters import BaseFilter
from aiogram.types import Message

from database import *

db = Database("users.db")


class SolverFilter(BaseFilter):
    async def __call__(self, message: Message):
        return db.solver_exist(Solver(message.chat.id))