from pydantic import BaseModel

from schemas.mongo import Audio, File, Image


class CreateSession(BaseModel):
    prompt: str
    audio: Audio | None
    files: list[File]
    images: list[Image]


class CreateProject(BaseModel):
    name: str
    goal: str


class UpdateProjectSession(BaseModel):
    ids: list[str]


class SimilarSessions(BaseModel):
    uid: str
    threshold: float
    limit: int
