from typing import Optional
from models.mongo import Message, Session


class DataBase(Session):
    def fetch_session(self, name: str):
        session = self._object_key.get(session_name=name)
        return session

    def fetch_all_session(self):
        sessions = self._object_key()
        return sessions

    def add_message(self, role: str, content: str):
        self.messages.append(Message(role=role, content=content))
        self.save()

    def delete_message(self, idx: int):
        self.messages.pop(idx)
        self.save()

    def fetch_messages(self):
        messages = [{"role": m.role, "content": m.content} for m in self.messages]
        return messages
