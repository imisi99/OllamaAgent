from typing import Any
from pydantic import BaseModel


class UpdateMemory(BaseModel):
    key: str
    value: Any
