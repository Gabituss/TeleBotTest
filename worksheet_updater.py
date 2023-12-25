import pygsheets
from pygsheets.exceptions import WorksheetNotFound

import numpy as np
from database import *
from functools import cmp_to_key
from datetime import datetime


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


def check(task: Task):
    dt = date.today()
    date1 = date.fromisoformat(task.deadline.split()[0])

    return date1 >= dt


def clear(sheet):
    sheet.update_values('A2', [["" for i in range(10)] for j in range(1000)])


class Updater:
    def __init__(self, path, dbpath):
        self.client = pygsheets.authorize(service_file=path)
        self.sh = self.client.open("tasks")
        self.db = Database(dbpath)

    def add_tasks(self, tasks, sheet, start):
        if len(tasks) <= 0:
            return

        sheet.update_values(f'A{start}', [
            [
                self.db.get_test(task.type_id).description,
                task.deadline,
                task.user_name,
                task.login_data.split()[0],
                task.login_data.split()[1],
                task.mark,
                task.approved,
                f"/start_task {task.task_id}",
                f"/finish_task {task.task_id} оценка",
            ] for task in tasks
        ])

    def update_tasks_list(self):
        tasks = self.db.get_all_tasks()
        tasks = sorted(tasks, key=cmp_to_key(compare))
        types = dict()
        for task in tasks:
            if not check(task):
                continue

            types["главное"] = types.get("главное", []) + [task]
            types[task.test_name] = types.get(task.test_name, []) + [task]

        for tp, task in types.items():
            try:
                wks = self.sh.worksheet_by_title(tp)
            except WorksheetNotFound:
                wks = self.sh.add_worksheet(tp)
            wks.update_values('A1', [["Тип теста", "Дедлайн", "ФИО", "Логин", "Пароль", "Оценка", "Подтвержден",
                                      "Команда для начала работы", "Команда для конца работы"]])
            clear(wks)
            tasks3 = list(filter(lambda t: t.approved == 3 and check(t), task))
            tasks2 = list(filter(lambda t: t.approved == 2 and check(t), task))
            tasks1 = list(filter(lambda t: t.approved == 1 and check(t), task))

            self.add_tasks(tasks3, wks, 2)
            self.add_tasks(tasks2, wks, 3 + len(tasks3))
            self.add_tasks(tasks1, wks, 4 + len(tasks3) + len(tasks2))
