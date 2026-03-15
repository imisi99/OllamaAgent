import random
from typing import Any
from schemas.mongo import Message, Session, User


class MockDatabase:
    def __init__(self) -> None:
        self.call_fail = 0
        self.delete = 0
        self.session: dict[str, Session] = {}
        self.user: dict[str, User] = {}

    def create_session(self, session: Session) -> tuple[bool, str]:
        id = str(random.randrange(0, 4)) + "abc" + str(random.randrange(5, 9))
        session["_id"] = id
        self.session[id] = session
        return True, session["_id"]

    def fetch_session(self, session_id: str) -> Session | None:
        if session_id in self.session.keys():
            session = self.session[session_id]
            return session
        return None

    def fetch_all_session(self) -> list[Session] | None:
        if len(self.session) == 0:
            return None
        sessions = [session for _, session in self.session.items()]
        print(sessions)
        return sessions

    def add_messages(self, session_id: str, message: Message) -> bool:
        if session_id in self.session.keys():
            session = self.session[session_id]
            session["messages"].append(message)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.session.keys():
            self.session.pop(session_id)
            return True
        return False

    def fetch_user(self, user_id: str) -> User | None:
        if user_id in self.user:
            return self.user[user_id]
        return None

    def update_user_memory(self, user_id: str, key: str, value: Any) -> bool:
        if user_id in self.user:
            user = self.user[user_id]
            user["memory"][key] = value
            return True
        return False
