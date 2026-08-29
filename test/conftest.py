from datetime import datetime
from core.agent import get_model
from core.conf import CustomError
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from main import app

import json
import logging
from typing import Any, cast
from uuid import uuid4

from schemas.agent import SessionState
from schemas.mongo import Message, Project, Session, User
from schemas.qdrant import QMessage, QSession
from core.qdrant import Task, Job


class MockModel:
    def log_llm_response(self, response, label: str = "LLM"):
        logging.info(f"Testing if this works, {response}, {label}")

    def generate_title(self, content, audio) -> str:
        return content

    def summarize_messagess(self, messages: list[Message]) -> str | None:
        return json.dumps(messages)

    async def chat(self, prompt: SessionState) -> dict[str, Any]:
        response = {"response": "Yep this should return very quickly"}
        return response


class MockDatabase:
    def __init__(self) -> None:
        self.delete = 0
        self.message: dict[str, Message] = {}
        self.session: dict[str, Session] = {}
        self.project: dict[str, Project] = {}
        self.user: dict[str, User] = {}

    def normalize_datetime(self, date: datetime | str) -> str:
        if isinstance(date, datetime):
            return date.isoformat()
        return date

    def create_session(self, session: Session) -> tuple[CustomError | None, str]:
        id = str(uuid4())
        session["_id"] = id
        session["created_at"] = self.normalize_datetime(session["created_at"])
        session["last_edited"] = self.normalize_datetime(session["last_edited"])
        self.session[id] = session
        return None, session["_id"]

    def create_message(self, message: Message) -> CustomError | None:
        id = str(uuid4())
        message["timestamp"] = self.normalize_datetime(message["timestamp"])
        self.message[id] = message
        return None

    def fetch_sessions(self, ids: list[str]) -> list[Session]:
        return [sess for sess in self.session.values()]

    def fetch_session(
        self, session_id: str
    ) -> tuple[CustomError | None, Session | None, list[Message]]:
        if session_id in self.session:
            return (
                None,
                self.session[session_id],
                [
                    msg
                    for msg in self.message.values()
                    if msg["session_id"] == session_id
                ],
            )
        return CustomError(message="Session not found.", code=404), None, []

    def fetch_all_session_preview(self) -> list[Session]:
        sessions = []
        for _, session in self.session.items():
            sessions.append(
                {
                    "_id": session["_id"],
                    "uuid": session["uuid"],
                    "name": session["name"],
                    "created_at": "",
                }
            )

        return sessions

    def fetch_all_session(self) -> list[tuple[Session, list[Message]]]:
        result = []
        for session in self.session.values():
            msgs = []
            for msg in self.message.values():
                if msg["session_id"] == session["_id"]:
                    msgs.append(msg)

            result.append((session, msgs))
        return result

    def rename_session(self, session_id: str, name: str) -> CustomError | None:
        if session_id not in self.session:
            return CustomError(message="Session not found.", code=404)
        else:
            self.session[session_id]["name"] = name
            return None

    def delete_session(self, session_id: str) -> CustomError | None:
        if session_id in self.session:
            self.session.pop(session_id)
            return None
        return CustomError(message="Session not found.", code=404)

    def create_project(self, project: Project) -> tuple[CustomError | None, str]:
        id = str(uuid4())
        project["_id"] = id
        project["created_at"] = self.normalize_datetime(project["created_at"])
        self.project[id] = project
        return None, id

    def edit_project_details(self, name: str, goal: str, id: str) -> CustomError | None:
        if id in self.project:
            self.project[id]["goal"] = goal
            self.project[id]["name"] = name
            return None
        return CustomError(message="Project not found.", code=404)

    def fetch_projects(self) -> list[Project]:
        return [project for project in self.project.values()]

    def fetch_project(
        self, project_id: str
    ) -> tuple[CustomError | None, Project | None, list[Session]]:
        if project_id in self.project:
            return (
                None,
                self.project[project_id],
                [
                    sess
                    for sess in self.session.values()
                    if sess["project_id"] == project_id
                ],
            )
        return CustomError(message="Project not found.", code=404), None, []

    def fetch_all_project_exclude_one(self, project_id: str) -> list[Project]:
        return [proj for proj in self.project.values() if proj["_id"] != project_id]

    def add_session_to_project(
        self, ids: list[str], project_id: str
    ) -> CustomError | None:
        if project_id not in self.project:
            return CustomError(message="Project not found.", code=404)

        failed_sess = False
        for id in ids:
            if id in self.session:
                self.session[id]["project_id"] = project_id
            else:
                failed_sess = True

        if failed_sess:
            return CustomError(message="A session did not exist.", code=404)
        return None

    def remove_session_from_project(
        self, ids: list[str], project_id: str
    ) -> CustomError | None:
        if project_id not in self.project:
            return CustomError(message="Project not found.", code=404)

        failed_sess = False
        for id in ids:
            if id in self.session and self.session[id]["project_id"] == project_id:
                self.session[id]["project_id"] = ""
            else:
                failed_sess = True

        if failed_sess:
            return CustomError(message="A session did not exist.", code=404)
        return None

    def delete_project(self, project_id: str) -> CustomError | None:
        if project_id in self.project:
            self.project.pop(project_id)
            return None

        return CustomError(message="Project not found.", code=404)

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
        self.points: dict[str, QSession] = {}
        self.tasks: list[Task] = []

    async def create_point(self, session: QSession) -> CustomError | None:
        self.points[session.uuid] = session
        return None

    async def update_point(self, uid: str, message: QMessage) -> CustomError | None:
        if id in self.points:
            self.points[uid].messages.append(message)
            return None
        return CustomError(message="Session not found.", code=404)

    async def update_payload(self, id: str, name: str) -> CustomError | None:
        if id in self.points:
            self.points[id].name = name
            return None
        return CustomError(message="Session not found.", code=404)

    async def delete_point(self, id: str) -> CustomError | None:
        if id in self.points:
            self.points.pop(id)
            return None
        return CustomError(message="Session not found.", code=404)

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
                        await self.create_point(cast(QSession, task.session))
                    case Job.UPDATE_POINT:
                        await self.update_point(task.uid, cast(QMessage, task.message))
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
