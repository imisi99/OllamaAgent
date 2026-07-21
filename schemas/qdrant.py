from typing import TypedDict


class QMessage(TypedDict):
    role: str
    content: str


class QSession(TypedDict):
    _id: str
    uuid: str
    name: str
    project_id: str
    messages: list[QMessage]
