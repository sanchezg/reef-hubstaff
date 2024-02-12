import abc
import os
import sqlite3
from datetime import date, datetime
from typing import Any, Generic, Optional, TypeVar

from src.models import Activity, Organization, Project, User

T = TypeVar("T")


class AbstractRepo(abc.ABC, Generic[T]):
    @abc.abstractmethod
    def get_one(self, **kwargs) -> Optional[T]:
        pass

    @abc.abstractmethod
    def get(self, **kwargs) -> Optional[list]:
        pass

    @abc.abstractmethod
    def insert(self, **kwargs) -> None:
        pass


class SQLiteRepo(AbstractRepo):
    def __init__(self) -> None:
        self._connector = sqlite3.connect(os.environ.get("DB_FILENAME", "hubstaff.db"))
        self._cursor = self._connector.cursor()
        super().__init__()

    def create_table(self, table: str, columns: dict[str, str]) -> None:
        query = f"CREATE TABLE IF NOT EXISTS {table} ("
        query += ", ".join([f"{k} {v}" for k, v in columns.items()])
        query += ")"
        self._cursor.execute(query)
        self._connector.commit()

    def get(self, table, **kwargs) -> Optional[Any]:
        query = f"SELECT * FROM {table}"
        if kwargs.get("filters"):
            query += " WHERE "
            query += " AND ".join([f"{k}={v}" for k, v in kwargs.get("filters").items()])

        res = self._cursor.execute(query)
        return res.fetchall()

    def get_one(self, table, **kwargs) -> Optional[Any]:
        query = f"SELECT * FROM {table}"
        if kwargs.get("filters"):
            query += " WHERE "
            query += " AND ".join([f"{k}={v}" for k, v in kwargs.get("filters").items()])

        res = self._cursor.execute(query)
        return res.fetchone()

    def insert(self, table, **kwargs) -> None:
        values = kwargs.get("values")  # values is a list of tuples
        query = "INSERT"
        if kwargs.get("on_conflict"):
            query += f" OR {kwargs.get('on_conflict')}"
        query += f" INTO {table} VALUES ({('?,' * len(values[0])).rstrip(',')})"
        self._cursor.executemany(query, values)
        self._connector.commit()


class ActivityBaseRepo(AbstractRepo[Activity], metaclass=abc.ABCMeta):
    pass


class ActivityRepo(SQLiteRepo, ActivityBaseRepo):
    entity = Activity

    def create_table(self) -> None:
        table = "activities"
        columns = {
            "id": "INTEGER PRIMARY KEY",
            "date": "DATE UNIQUE",
            "user_id": "INTEGER",
            "project_id": "INTEGER",
            "task_id": "INTEGER",
            "keyboard": "INTEGER",
            "mouse": "INTEGER",
            "overall": "INTEGER",
            "tracked": "INTEGER",
            "input_tracked": "INTEGER",
            "manual": "INTEGER",
            "idle": "INTEGER",
            "resumed": "INTEGER",
            "billable": "INTEGER",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        }

        return super().create_table(table, columns)

    def get(self, **kwargs) -> list[Activity] | None:
        rows = super().get(table="activities")
        if kwargs.get("raw_data"):
            return rows

        if rows:
            return [
                Activity(
                    id=row[0],
                    date=date.fromisoformat(row[1]),
                    user_id=row[2],
                    project_id=row[3],
                    task_id=row[4],
                    keyboard=row[5],
                    mouse=row[6],
                    overall=row[7],
                    tracked=row[8],
                    input_tracked=row[9],
                    manual=row[10],
                    idle=row[11],
                    resumed=row[12],
                    billable=row[13],
                    created_at=datetime.fromisoformat(row[14]),
                    updated_at=datetime.fromisoformat(row[15])
                )
                for row in rows
            ]

    def insert(self, activities: list[Activity]) -> None:
        table = "activities"
        values = [
            (obj.id, obj.date.isoformat(), obj.user_id, obj.project_id, obj.task_id, obj.keyboard, obj.mouse, obj.overall, obj.tracked, obj.input_tracked, obj.manual, obj.idle, obj.resumed, obj.billable, obj.created_at.isoformat(), obj.updated_at.isoformat())
            for obj in activities
        ]
        return super().insert(table, values=values, on_conflict="REPLACE")


class ProjectBaseRepo(AbstractRepo[Project], metaclass=abc.ABCMeta):
    pass


class ProjectRepo(SQLiteRepo, ProjectBaseRepo):
    entity = Project

    def create_table(self) -> None:
        table = "projects"
        columns = {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
            "status": "TEXT",
            "billable": "INTEGER",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        }

        return super().create_table(table, columns)

    def get(self, **kwargs) -> list[Project] | None:
        rows = super().get(table="projects", filters={"organization_id": kwargs.get("organization_id")})
        if rows:
            return [
                Project(
                    id=row[0],
                    name=row[1],
                    status=row[2],
                    billable=bool(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5])
                )
                for row in rows
            ]

    def insert(self, projects: list[Project]) -> None:
        values = [
            (obj.id, obj.name, obj.status, obj.billable, obj.created_at.isoformat(), obj.updated_at.isoformat())
            for obj in projects
        ]
        return super().insert(table="projects", values=values, on_conflict="IGNORE")


class UserBaseRepo(AbstractRepo[User], metaclass=abc.ABCMeta):
    pass


class UserRepo(SQLiteRepo, UserBaseRepo):
    entity = User

    def create_table(self) -> None:
        table = "users"
        columns = {
            "id": "INTEGER PRIMARY KEY",
            "name": "TEXT",
            "email": "TEXT UNIQUE",
            "time_zone": "TEXT",
            "status": "TEXT",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        }
        return super().create_table(table, columns)
