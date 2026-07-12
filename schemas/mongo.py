from datetime import datetime
from typing import Any, TypedDict


class Image(TypedDict):
    image: Any
    mime: str
    name: str


class File(TypedDict):
    file: Any
    name: str


class Audio(TypedDict):
    audio: Any
    mime: str
    transcript: str


class Message(TypedDict):
    role: str
    content: str
    audio: Audio | None
    thought: str
    files: list[File]
    images: list[Image]
    timestamp: datetime | str


class Session(TypedDict):
    _id: str
    uuid: str
    name: str
    created_at: datetime | str
    messages: list[Message]

class Project(TypedDict):
    _id: str
    name: str
    sessions: list[Session]


class User(TypedDict):
    _id: str
    name: str
    memory: dict[str, Any]
