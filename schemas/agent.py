from typing import TypedDict


from .mongo import Message


class SessionConversation(TypedDict):
    user_id: str
    session_id: str
    message: Message
    ghost_session: bool


class SessionState(SessionConversation):
    response: str
