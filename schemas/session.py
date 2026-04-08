from pydantic import BaseModel


class CreateSession(BaseModel):
    prompt: str
