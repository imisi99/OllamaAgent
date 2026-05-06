from datetime import datetime
from typing import Any, TypedDict


class Image(TypedDict):
    image: Any
    mime: str
    name: str


class Message(TypedDict):
    role: str
    content: str
    files: list[tuple[Any, str]]
    images: list[Image]
    timestamp: datetime | str


class Session(TypedDict):
    _id: str
    uuid: str
    name: str
    created_at: datetime | str
    messages: list[Message]


class User(TypedDict):
    _id: str
    name: str
    memory: dict[str, Any]
