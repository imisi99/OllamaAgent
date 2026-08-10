from pydantic import BaseModel


class CreateProject(BaseModel):
    name: str
    goal: str


class UpdateProjectSession(BaseModel):
    ids: list[str]
