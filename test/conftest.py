from core.agent import get_model
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from main import app

import json
import logging
from typing import Any, cast
from uuid import uuid4

from schemas.agent import SessionState
from schemas.mongo import Message, Session, User
from core.qdrant import Task, Job


class MockModel:
    def log_llm_response(self, response, label: str = "LLM"):
        logging.info(f"Testing if this works, {response}, {label}")

    def generate_title(self, content) -> str:
        return content

    def summarize_messagess(self, messages: list[Message]) -> str | None:
        return json.dumps(messages)

    def chat(self, prompt: SessionState) -> dict[str, Any]:
        response = {"response": "Yep this should return very quickly"}
        return response


class MockDatabase:
    def __init__(self) -> None:
        self.delete = 0
        self.session: dict[str, Session] = {}
        self.user: dict[str, User] = {}

    def create_session(self, session: Session) -> tuple[bool, str]:
        id = str(uuid4())
        session["_id"] = id
        self.session[id] = session
        return True, session["_id"]

    def fetch_sessions(self, ids: list[str]) -> list[Session]:
        sessions = []
        for id in ids:
            if id in self.session:
                sessions.append(self.session[id])
        return sessions

    def fetch_session(self, session_id: str) -> Session | None:
        if session_id in self.session:
            session = self.session[session_id]
            return session
        return None

    def fetch_all_session_preview(self) -> list[Session]:
        sessions = []
        for _, session in self.session.items():
            sessions.append(
                Session(
                    {
                        "_id": session["_id"],
                        "uuid": session["uuid"],
                        "name": session["name"],
                        "created_at": "",
                        "messages": [],
                    }
                )
            )

        return sessions

    def fetch_all_session(self) -> list[Session] | None:
        sessions = [session for _, session in self.session.items()]
        return sessions

    def rename_session(self, session_id: str, name: str) -> bool:
        if session_id not in self.session:
            return False
        else:
            self.session[session_id]["name"] = name
            return True

    def add_messages(self, session_id: str, message: Message) -> bool:
        if session_id in self.session:
            session = self.session[session_id]
            session["messages"].append(message)
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.session:
            self.session.pop(session_id)
            return True
        return False

    def create_user(self, username: str) -> tuple[str, bool]:
        id = str(uuid4())
        self.user[id] = User({"_id": id, "name": username, "memory": {}})
        return id, True

    def fetch_user_id(self) -> str | None:
        for id in self.user:
            return id
        return None

    def fetch_user(self, user_id: str) -> User | None:
        if user_id in self.user:
            return self.user[user_id]
        return None

    def update_user_name(self, user_id: str, name: str) -> bool:
        if user_id in self.user:
            self.user[user_id]["name"] = name
            return True
        return False

    def update_user_memory(self, user_id: str, key: str, value: Any) -> bool:
        if user_id in self.user:
            user = self.user[user_id]
            user["memory"][key] = value
            return True
        return False

    def remove_user_memory(self, user_id: str, key: str) -> bool:
        if user_id in self.user:
            self.user[user_id]["memory"].pop(key)
            return True
        return False


class MockQdrant:
    def __init__(self) -> None:
        self.points: dict[str, Session] = {}
        self.tasks: list[Task] = []

    async def create_point(self, session: Session) -> bool:
        self.points[session["uuid"]] = session
        return True

    async def update_point(self, id: str, message: Message) -> bool:
        if id in self.points:
            self.points[id]["messages"].append(message)
            return True
        return False

    async def update_payload(self, id: str, name: str) -> bool:
        if id in self.points:
            self.points[id]["name"] = name
            return True
        return False

    async def delete_point(self, id: str) -> bool:
        if id in self.points:
            self.points.pop(id)
            return True
        return False

    def add_job(self, task: Task):
        self.tasks.append(task)

    async def worker(self):
        while True:
            if len(self.tasks) == 0:
                continue
            else:
                task = self.tasks.pop(0)
                match task.job:
                    case Job.CREATE_POINT:
                        await self.create_point(cast(Session, task.session))
                    case Job.UPDATE_POINT:
                        await self.update_point(task.uid, cast(Message, task.message))
                    case Job.DELETE_POINT:
                        await self.delete_point(task.uid)
                    case Job.UPDATE_PAYLOAD:
                        await self.update_payload(task.uid, task.name)


db = MockDatabase()
qdb = MockQdrant()
model = MockModel()


def mock_db() -> Any:
    return db


def mock_qdb() -> Any:
    return qdb


def mock_model() -> Any:
    return model


app.dependency_overrides[get_model] = mock_model
app.dependency_overrides[get_mongo_database] = mock_db
app.dependency_overrides[get_qdrant_database] = mock_qdb
