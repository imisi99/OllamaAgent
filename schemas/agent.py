from typing import TypedDict, Any


from .mongo import Message


class SessionConversation(TypedDict):
    user_id: str
    session_id: str
    message: Message
    ghost_session: bool


class SessionState(SessionConversation):
    model: Any
    response: str
