from typing import TypedDict
from langchain.agents import AgentState

from schemas.qdrant import QChunk


from .mongo import Message


class SessionConversation(TypedDict):
    user_id: str
    session_id: str
    session_uid: str
    message: Message
    ghost_session: bool


class SessionState(SessionConversation):
    response: str
    chunks: list[QChunk]


class SessAgentState(AgentState):
    session_id: str
    session_uid: str
    ghost_session: bool
    user_id: str
