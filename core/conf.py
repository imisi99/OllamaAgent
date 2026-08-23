from pydantic import BaseModel


class CustomError(BaseModel):
    def __init__(self, message: str, code: int) -> None:
        self.message = message
        self.code = code

    def error(self) -> str:
        return f"An error occured -> {self.message} with code -> {self.code}"
