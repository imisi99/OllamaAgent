from datetime import datetime
from typing import TypedDict


class Message(TypedDict):
    role: str
    content: str
    timestamp: datetime


class Session(TypedDict):
    name: str
    created_at: datetime
    messages: list[Message]


class User(TypedDict):
    name: str
