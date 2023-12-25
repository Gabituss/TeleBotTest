import pygsheets
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


class Updater:
    def __init__(self, path, dbpath):
        self.client = pygsheets.authorize(service_file=path)
        self.sh = self.client.open("tasks")
        self.wks: pygsheets.worksheet.Worksheet = self.sh.sheet1
        self.db = Database(dbpath)

    def clear(self):
        self.wks.update_values('A2', [["" for i in range(10)] for j in range(1000)])

    def update_cell_mark(self, mark, cell):
        self.wks.update_value(cell, mark)

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
        if len(tasks) > 0:
            types = dict()
            tasks3 = list(filter(lambda task: task.approved == 3 and check(task), tasks))
            tasks2 = list(filter(lambda task: task.approved == 2 and check(task), tasks))
            tasks1 = list(filter(lambda task: task.approved == 1 and check(task), tasks))

            self.add_tasks(tasks3, self.wks, 2)
            self.add_tasks(tasks2, self.wks, 3 + len(tasks3))
            self.add_tasks(tasks1, self.wks, 4 + len(tasks3) + len(tasks2))
