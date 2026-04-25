from typing import TypedDict
from langchain.agents import AgentState


from .mongo import Message


class SessionConversation(TypedDict):
    user_id: str
    session_id: str
    session_uid: str
    message: Message
    ghost_session: bool


class SessionState(SessionConversation):
    response: str
    chunks: list[str]


class SessAgentState(AgentState):
    session_id: str
    ghost_session: bool
    user_id: str
