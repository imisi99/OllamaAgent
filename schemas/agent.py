from typing import TypedDict

from langchain_ollama import ChatOllama
from mongo import Message


class SessionConversation(TypedDict):
    session_id: str
    message: Message


class SessionState(SessionConversation):
    llm: ChatOllama
    response: str
