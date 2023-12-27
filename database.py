import random
import sqlite3 as sql
from datetime import date, datetime, time
from random import randint


def gen_id():
    return randint(0, 1000000000)


class User:
    def __init__(self, id_, name):
        self.id = (gen_id() if id_ == -1 else id_)
        self.name = name


class Solver:
    def __init__(self, id_):
        self.id = id_


class Task:
    def __init__(self, type_id: int, task_id: int, user_id: int, test_name: str, login_data: str, deadline,
                 mark=-1, user_name="ФИО", approved=2):
        self.type_id = type_id
        self.task_id = (task_id if task_id != -1 else gen_id())
        self.user_id = user_id
        self.user_name = user_name
        self.test_name = test_name
        self.login_data = login_data
        self.deadline = deadline
        self.mark = mark
        if mark == -1:
            self.as_str = f"Тест \"{test_name}\" до {self.deadline} ⏳"
        else:
            self.as_str = f"Тест \"{test_name}\" решен, оценка - {mark} ✅"
        self.approved = approved


class Test:
    def __init__(self, test_id, cost, description, available=True):
        self.test_id = (test_id if test_id != -1 else gen_id())
        self.description = description
        self.cost = cost
        self.available = available

    def __str__(self):
        return f"{self.description} {self.cost}₽"


class Database:
    def __init__(self, path):
        self.connection = sql.connect(path)
        self.cursor = self.connection.cursor()

        self.connection.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER primary key,
            full_name TEXT
        );
        
        ''')  # Create Table of users
        self.connection.execute('''
        CREATE TABLE IF NOT EXISTS Tasks (
            type_id INTEGER,
            task_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            test_name TEXT,
            login_data TEXT,
            deadline TEXT,
            mark INTEGER,
            user_name TEXT,
            approved INT
        )
        ''')  # Create Table of user tasks
        self.connection.execute('''
        CREATE TABLE IF NOT EXISTS Tests (
            test_id INTEGER PRIMARY KEY,
            cost INTEGER,
            description TEXT
            available INT
        )
        ''')  # Create Table of tests
        self.connection.execute('''
        CREATE TABLE IF NOT EXISTS Solvers (
            id INTEGER PRIMARY KEY
        )
        ''')  # Create Table of solvers
        self.connection.execute('''
        CREATE TABLE IF NOT EXISTS TimeDeltas (
            type TEXT PRIMARY KEY,
            time TEXT
        )''')

        self.connection.execute('INSERT OR IGNORE INTO TimeDeltas (type, time) VALUES (?, ?)', ("from", "06:00"))
        self.connection.execute('INSERT OR IGNORE INTO TimeDeltas (type, time) VALUES (?, ?)', ("to", "18:00"))
        self.connection.commit()

    def get_time_deltas(self):
        self.cursor.execute('SELECT time FROM TimeDeltas')
        vals = list(map(lambda x: time.fromisoformat(x[0]), self.cursor.fetchall()))
        if vals[0] > vals[1]:
            vals[0], vals[1] = vals[1], vals[0]
        return vals

    def update_time_deltas(self, start, end):
        self.connection.execute('UPDATE TimeDeltas SET time=? WHERE type=?', (start, "from"))
        self.connection.execute('UPDATE TimeDeltas SET time=? WHERE type=?', (end, "to"))
        self.connection.commit()

    # region user
    def add_user(self, user: User) -> None:
        self.connection.execute('INSERT OR IGNORE INTO Users (id, full_name) VALUES (?, ?)', (user.id, user.name))
        self.connection.commit()

    def remove_user(self, user_id):
        self.connection.execute('DELETE FROM Users WHERE id=(?)', (user_id,))
        self.connection.commit()

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM Users WHERE id=(?)', (user_id,))
        user = self.cursor.fetchone()
        return User(user[0], user[1])

    def get_users(self):
        self.cursor.execute('SELECT id FROM Users')
        ids = list(map(lambda x: x[0], self.cursor.fetchall()))
        users = [self.get_user(id) for id in ids]
        users.sort(key=lambda user: user.name)
        return users

    def user_exists(self, user_id) -> bool:
        self.cursor.execute('SELECT COUNT(*) FROM Users WHERE id = (?)', (user_id,))
        return self.cursor.fetchone()[0] > 0

    # endregion
    # region test
    def add_test(self, test: Test):
        self.connection.execute('INSERT INTO Tests (test_id, cost, description) VALUES (?, ?, ?)',
                                (test.test_id, test.cost, test.description))
        self.connection.commit()

    def remove_test(self, test_id):
        self.connection.execute('UPDATE Tests SET available=(?) WHERE test_id=(?)', (False, test_id))
        self.connection.execute('DELETE FROM Tests WHERE test_id=(?)', (test_id,))
        self.connection.commit()

    def update_test(self, test_id, test: Test):
        self.connection.execute('UPDATE Tests SET cost=?, description=? WHERE test_id=(?)',
                                (test.cost, test.description, test_id))
        self.connection.commit()

    def get_test(self, test_id):
        self.cursor.execute('SELECT * FROM Tests WHERE test_id = (?)', (test_id,))
        test = self.cursor.fetchone()
        return Test(test[0], test[1], test[2])

    def get_test_list(self):
        self.cursor.execute('SELECT * FROM Tests WHERE avaiable!=0')
        tests = list(map(lambda x: Test(*x), self.cursor.fetchall()))
        return tests

    # endregion
    # region task
    def add_task(self, task: Task):
        self.connection.execute(
            'INSERT INTO Tasks (type_id, task_id, user_id, test_name, login_data, deadline, mark, user_name, approved) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (task.type_id, task.task_id, task.user_id, task.test_name, task.login_data, task.deadline, task.mark,
             task.user_name, task.approved))
        self.connection.commit()

    def update_task(self, task_id, task: Task):
        self.connection.execute('''
        UPDATE Tasks SET type_id=(?), task_id=(?), user_id=(?), test_name=(?),login_data=(?),deadline=(?),mark=(?),user_name=(?),approved=(?)
        WHERE task_id=(?)
        ''', (task.type_id, task.task_id, task.user_id, task.test_name, task.login_data, task.deadline, task.mark,
              task.user_name, task.approved, task_id))
        self.connection.commit()

    def remove_task(self, task_id):
        self.connection.execute('DELETE FROM Tasks WHERE task_id=(?)', (task_id,))
        self.connection.commit()

    def get_task(self, task_id):
        self.cursor.execute('SELECT * FROM Tasks WHERE task_id=(?)', (task_id,))
        task = self.cursor.fetchone()

        return Task(
            type_id=task[0],
            task_id=task[1],
            user_id=task[2],
            test_name=task[3],
            login_data=task[4],
            deadline=task[5],
            mark=task[6],
            user_name=task[7],
            approved=task[8]
        )

    def update_task_mark(self, task_id, mark):
        self.connection.execute('UPDATE Tasks SET mark=(?) WHERE task_id=(?)', (mark, task_id))
        self.connection.commit()

    def update_task_approve_status(self, task_id, status):
        self.connection.execute('UPDATE Tasks SET approved=(?) WHERE task_id=(?)', (status, task_id))
        self.connection.commit()

    def get_tasks(self, user_id):
        self.cursor.execute('SELECT task_id FROM Tasks WHERE user_id=(?)', (user_id,))
        ids = list(map(lambda x: x[0], self.cursor.fetchall()))

        return [self.get_task(id_) for id_ in ids]

    def get_all_tasks(self):
        self.cursor.execute('SELECT task_id FROM Tasks')
        ids = list(map(lambda x: x[0], self.cursor.fetchall()))

        return [self.get_task(id_) for id_ in ids]

    # endregion
    # region admins
    def add_solver(self, solver):
        self.connection.execute('INSERT OR IGNORE INTO Solvers (id) VALUES (?)', (solver.id,))
        self.connection.commit()

    def remove_solver(self, solver):
        self.connection.execute('DELETE FROM Solvers WHERE id=(?)', (solver.id,))
        self.connection.commit()

    def solver_exist(self, solver):
        self.cursor.execute('SELECT COUNT(*) FROM Solvers WHERE id=(?)', (solver.id,))
        return self.cursor.fetchone()[0] > 0
    # endregion


if __name__ == '__main__':
    from itertools import product
    from datetime import datetime

    db = Database("users.db")
    db.add_solver(Solver(1173441935))
