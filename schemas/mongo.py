from datetime import datetime
from typing import Any, TypedDict


class Message(TypedDict):
    role: str
    content: str
    timestamp: str


class Session(TypedDict):
    _id: str
    name: str
    created_at: str
    messages: list[Message]


class User(TypedDict):
    name: str
    memory: dict[str, Any]
