from pydantic import BaseModel
from typing import Any

from schemas.mongo import File, Image


class CreateSession(BaseModel):
    prompt: str
    audio: Any
    files: list[File]
    images: list[Image]


class SimilarSessions(BaseModel):
    uid: str
    threshold: float
    limit: int
