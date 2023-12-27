import pygsheets
from pygsheets.exceptions import WorksheetNotFound
from pygsheets import Worksheet
from googleapiclient.errors import HttpError
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
    sheet.clear(fields="*")


def convert(task: Task):
    return [
        task.test_name,
        task.deadline,
        task.user_name,
        task.login_data.split()[0],
        task.login_data.split()[1],
        task.mark,
        task.approved,
        f"/start_task {task.task_id}",
        f"/finish_task {task.task_id} оценка"
    ]


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
                task.test_name,
                task.deadline,
                task.user_name,
                task.login_data.split()[0],
                task.login_data.split()[1],
                task.mark,
                task.approved,
                f"/start_task {task.task_id}",
                f"/finish_task {task.task_id} оценка",
                f"/write {task.task_id} текст",
            ] for task in tasks
        ])

    def create_worksheet(self, tp):
        wks = self.sh.add_worksheet(tp, rows=2000)
        wks.add_conditional_formatting('G2', f'G1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'green': 1}},
                                       ['3', '3'])
        wks.add_conditional_formatting('G2', f'G1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'green': 1, 'red': 1}},
                                       ['2', '2'])
        wks.add_conditional_formatting('G2', f'G1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'red': 1}},
                                       ['1', '1'])
        wks.add_conditional_formatting('F2', f'F1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'green': 1}},
                                       ['1', '5'])
        wks.add_conditional_formatting('F2', f'F1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'green': 1, 'red': 1}},
                                       ['0', '0'])
        wks.add_conditional_formatting('F2', f'F1500', 'NUMBER_BETWEEN',
                                       {'background_color': {'red': 1}},
                                       ['-1', '-1'])

        return wks

    def update_tasks_list(self):
        tasks = self.db.get_all_tasks()
        tasks = sorted(tasks, key=cmp_to_key(compare))
        types = dict()
        for task in tasks:
            if not check(task):
                continue

            types["главное"] = types.get("главное", []) + [task]
            types[task.test_name.split()[0]] = types.get(task.test_name.split()[0], []) + [task]

        for wks in self.sh.worksheets():
            if wks.title != "empty" and len(types.get(wks.title, [])) == 0:
                self.sh.del_worksheet(wks)

        for tp in self.db.get_test_list():
            try:
                wks = self.sh.worksheet_by_title(tp)
            except WorksheetNotFound or HttpError:
                wks = self.create_worksheet(tp)

            tasks = types[tp.description.split()[0]]

            clear(wks)
            wks.update_values('A1', [["Тип теста", "Дедлайн", "ФИО", "Логин", "Пароль", "Оценка", "Подтвержден",
                                      "Команда для начала работы", "Команда для конца работы",
                                      "Написать пользователю"]])

            tasks3 = list(filter(lambda t: t.approved == 3 and check(t), tasks))
            tasks2 = list(filter(lambda t: t.approved == 2 and check(t), tasks))
            tasks1 = list(filter(lambda t: t.approved == 1 and check(t), tasks))

            self.add_tasks(tasks3, wks, 2)
            self.add_tasks(tasks2, wks, 3 + len(tasks3))
            self.add_tasks(tasks1, wks, 4 + len(tasks3) + len(tasks2))
