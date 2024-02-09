from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class Organization:
    id: int


@dataclass
class Project:
    id: int
    name: str
    status: str
    billable: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class User:
    id: int
    name: str
    email: str
    time_zone: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass
class Activity:
    id: int
    date: date
    user_id: int
    project_id: int
    task_id: int
    keyboard: int
    mouse: int
    overall: int
    tracked: int
    input_tracked: int
    manual: int
    idle: int
    resumed: int
    billable: int
    created_at: datetime
    updated_at: datetime
