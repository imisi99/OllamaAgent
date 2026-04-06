from typing import TypedDict

from langchain_ollama import ChatOllama
from .mongo import Message


class SessionConversation(TypedDict):
    user_id: str
    session_id: str
    message: Message


class SessionState(SessionConversation):
    llm: ChatOllama
    response: str
