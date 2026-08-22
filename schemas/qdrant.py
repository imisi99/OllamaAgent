from typing import Any
from pydantic import BaseModel

from core.conf import CustomError


class QMessage(BaseModel):
    role: str
    content: str


class QSession(BaseModel):
    id: str
    uuid: str
    name: str
    project_id: str
    messages: list[QMessage] = []


class QChunk(BaseModel):
    text: str
    source: Any
    page: Any


class Similar(BaseModel):
    err: CustomError | None = None
    sessions: dict[QSession, float] = {}
    score: float = 0
