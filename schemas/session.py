from pydantic import BaseModel

from schemas.mongo import File, Image


class CreateSession(BaseModel):
    prompt: str
    files: list[File]
    images: list[Image]


class SimilarSessions(BaseModel):
    uid: str
    threshold: float
    limit: int
