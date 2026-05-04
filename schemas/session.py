from pydantic import BaseModel


class CreateSession(BaseModel):
    prompt: str


class SimilarSessions(BaseModel):
    uid: str
    threshold: float
    limit: int
