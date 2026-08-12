import base64
from datetime import datetime
import logging
from typing import Any, cast
from bson import ObjectId
from pymongo import MongoClient
from core.conf import CustomError
from schemas.mongo import Audio, File, Image, Message, Session, User, Project


class Database:
    def __init__(
        self,
        db: str,
        session: str,
        user: str,
        message: str,
        project: str,
        client: MongoClient[dict[str, Any]],
    ) -> None:
        self.db = db
        self.session = session
        self.user = user
        self.message = message
        self.project = project
        self.client = client
        self.session_collection = self.client[self.db][self.session]
        self.message_collection = self.client[self.db][self.message]
        self.project_collection = self.client[self.db][self.project]
        self.user_collection = self.client[self.db][self.user]

    def normalize_timestamp(self, timestamp: datetime | str) -> datetime:
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp)
        return timestamp

    def denormalize_timestamp(self, timestamp: datetime | str) -> str:
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        return timestamp

    def normalize_image_files(self, images: list[Image], files: list[File]):
        for image in images:
            image["image"] = base64.b64decode(image["image"])
        for file in files:
            file["file"] = base64.b64decode(file["file"])

    def denormalize_image_files(self, images: list[Image], files: list[File]):
        for image in images:
            image["image"] = base64.b64encode(image["image"]).decode()
        for file in files:
            file["file"] = base64.b64encode(file["file"]).decode()

    def normalize_audio(self, audio: Audio | None):
        if audio:
            if isinstance(audio["audio"], str):
                audio["audio"] = base64.b64decode(audio["audio"])

    def denormalize_audio(self, audio: Audio | None):
        if audio:
            if isinstance(audio["audio"], bytes):
                audio["audio"] = base64.b64encode(audio["audio"]).decode()

    def create_message(self, message: Message) -> CustomError | None:
        self.normalize_image_files(message["images"], message["files"])
        self.normalize_audio(message["audio"])
        message["timestamp"] = self.normalize_timestamp(message["timestamp"])

        result = self.message_collection.insert_one(
            {
                "role": message["role"],
                "content": message["content"],
                "audio": message["audio"],
                "thought": message["thought"],
                "files": message["files"],
                "images": message["images"],
                "session_id": message["session_id"],
                "timestamp": message["timestamp"],
            }
        )

        if not result.acknowledged:
            return CustomError(message="Failed to create message.", code=500)

    def create_session(self, session: Session) -> tuple[CustomError | None, str]:
        session["created_at"] = self.normalize_timestamp(session["created_at"])
        session["last_edited"] = self.normalize_timestamp(session["last_edited"])
        result = self.session_collection.insert_one(
            {
                "uuid": session["uuid"],
                "name": session["name"],
                "created_at": session["created_at"],
                "last_edited": session["last_edited"],
                "project_id": session["project_id"],
            }
        )
        if not result.acknowledged:
            return (
                CustomError(
                    message="Failed to create session",
                    code=500,
                ),
                "",
            )

        return None, str(result.inserted_id)

    def create_project(self, project: Project) -> tuple[CustomError | None, str]:
        project["created_at"] = self.normalize_timestamp(project["created_at"])
        result = self.project_collection.insert_one(
            {
                "name": project["name"],
                "goal": project["goal"],
                "created_at": project["created_at"],
            }
        )

        if not result.acknowledged:
            return CustomError(message="Failed to create project.", code=500), ""
        return None, str(result.inserted_id)

    def fetch_message(self, session_id: str) -> list[Message]:
        with self.message_collection.find(
            {"session_id": ObjectId(session_id)}
        ) as cursor:
            messages = list(cursor)

        for msg in messages:
            self.denormalize_audio(msg["audio"])
            self.denormalize_image_files(msg["images"], msg["files"])
            msg["timestamp"] = self.denormalize_timestamp(msg["timestamp"])

        messages = cast(list[Message], messages)
        return messages

    def fetch_message_for_redis(self, session_id: str) -> list[Message]:
        with self.message_collection.find(
            filter={"session_id": session_id},
            projection={
                "_id": False,
                "thought": False,
                "files": False,
                "timestamp": False,
            },
        ) as cursor:
            messages = list(cursor)

        for msg in messages:
            self.denormalize_audio(msg["audio"])
            self.denormalize_image_files(msg["images"], [])
            msg["timestamp"] = ""
            msg["files"] = []
            msg["thought"] = ""

        messages = cast(list[Message], messages)

        return messages

    def fetch_session(
        self, session_id: str
    ) -> tuple[CustomError | None, Session | None, list[Message]]:
        session = self.session_collection.find_one({"_id": ObjectId(session_id)})
        if session is not None:
            session["_id"] = str(session["_id"])
            session["created_at"] = self.denormalize_timestamp(session["created_at"])
            session["last_edited"] = self.denormalize_timestamp(session["last_edited"])
            messages = self.fetch_message(session_id)

            return None, cast(Session, session), messages

        return None, None, []

    def fetch_sessions(self, ids: list[str]) -> list[tuple[Session, list[Message]]]:
        with self.session_collection.find(
            {"_id": [ObjectId(id) for id in ids]}
        ) as cursor:
            sessions = list(cursor)

        result: list[tuple[Session, list[Message]]] = []
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["created_at"] = self.denormalize_timestamp(session["created_at"])
            session["last_edited"] = self.denormalize_timestamp(session["last_edited"])

            result.append((cast(Session, session), self.fetch_message(session["_id"])))

        return result

    def fetch_all_session(self) -> list[tuple[Session, list[Message]]]:
        with self.session_collection.find({}) as cursor:
            sessions = list(cursor)

        result: list[tuple[Session, list[Message]]] = []
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["created_at"] = self.denormalize_timestamp(session["created_at"])
            session["last_edited"] = self.denormalize_timestamp(session["last_edited"])

            result.append((cast(Session, session), self.fetch_message(session["_id"])))

        return result

    # TODO: Fetch in order of last message datetime && Also exclude the message resources
    def fetch_all_session_preview(self) -> list[Session]:
        with self.session_collection.find(filter={}, projection={}) as cursor:
            sessions = list(cursor)

        sessions.sort(key=lambda s: s["last_edited"])

        for session in sessions:
            session["_id"] = str(session["_id"])
            session["created_at"] = self.denormalize_timestamp(session["created_at"])
            session["last_edited"] = self.denormalize_timestamp(session["last_edited"])

        return cast(list[Session], sessions)

    def fetch_session_for_redis(
        self, session_id: str
    ) -> tuple[CustomError | None, list[Message]]:
        result = self.session_collection.find_one(filter={"_id": ObjectId(session_id)})

        if result is None:
            return CustomError(message="Session not found.", code=404), []

        return None, self.fetch_message_for_redis(session_id)

    def fetch_all_session_for_redis(self) -> list[tuple[Session, list[Message]]]:
        with self.session_collection.find(
            filter={},
            projection={
                "created_at": False,
                "last_edited": False,
            },
        ) as cursor:
            sessions = list(cursor)

        result: list[tuple[Session, list[Message]]] = []
        for session in sessions:
            session["_id"] = str(session["_id"])
            session["created_at"] = ""
            session["last_edited"] = ""

            result.append(
                (cast(Session, session), self.fetch_message_for_redis(session["_id"]))
            )

        logging.info(result)

        return result

    def fetch_project(
        self, project_id: str
    ) -> tuple[CustomError | None, Project | None, list[Session]]:
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})

        if not project:
            return CustomError(message="Project not found.", code=404), None, []

        with self.session_collection.find({"project_id": project_id}) as cursor:
            sessions = list(cursor)

        sessions.sort(key=lambda s: s["last_edited"])

        for session in sessions:
            session["_id"] = str(session["_id"])
            session["created_at"] = self.denormalize_timestamp(session["created_at"])
            session["last_edited"] = self.denormalize_timestamp(session["last_edited"])

        project["_id"] = str(project["_id"])
        project["created_at"] = self.denormalize_timestamp(project["created_at"])

        return None, cast(Project, project), cast(list[Session], sessions)

    def fetch_projects(self) -> list[Project]:
        with self.project_collection.find() as cursor:
            projects = list(cursor)

        for project in projects:
            project["_id"] = str(project["_id"])
            project["created_at"] = self.denormalize_timestamp(project["created_at"])

        return cast(list[Project], projects)

    def add_session_to_project(
        self, session_id: list[str], project_id: str
    ) -> CustomError | None:
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})

        if not project:
            return CustomError(message="Project doesn't exist.", code=404)

        failed_session = False

        for sess_id in session_id:
            session = self.session_collection.find_one_and_update(
                filter={"_id": ObjectId(sess_id)},
                update={"$set": {"project_id": project_id}},
            )

            if not session:
                failed_session = True

        if failed_session:
            return CustomError(message="A session deosn't exist.", code=404)

    def remove_session_from_project(
        self, session_id: list[str], project_id: str
    ) -> CustomError | None:
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})

        if not project:
            return CustomError(message="Project doesn't exist.", code=404)

        failed_session = False

        for sess_id in session_id:
            session = self.session_collection.find_one_and_update(
                filter={"_id": ObjectId(sess_id)},
                update={"$set": {"project_id": ""}},
            )

            if not session:
                failed_session = True

        if failed_session:
            return CustomError(message="A session deosn't exist.", code=404)

    def edit_project_details(
        self, name: str, goal: str, project_id: str
    ) -> CustomError | None:
        result = self.project_collection.update_one(
            {"_id": ObjectId(project_id)},
            update={"$set": {"name": name, "goal": goal}},
        )

        if result.matched_count == 0:
            return CustomError(message="The project doesn't exist", code=404)

        if not result.acknowledged:
            return CustomError(
                message="Editing of project was not acknowledged", code=500
            )

    def rename_session(self, session_id: str, name: str) -> CustomError | None:
        result = self.session_collection.update_one(
            {"_id": ObjectId(session_id)}, {"$set": {"name": name}}
        )

        if result.matched_count == 0:
            return CustomError(message="The session doesn't exist", code=404)

        if not result.acknowledged:
            return CustomError(
                message="Renaming of session was not acknowledged", code=500
            )

    def delete_session(self, session_id: str) -> CustomError | None:
        result = self.session_collection.delete_one({"_id": ObjectId(session_id)})

        if not result.acknowledged:
            return CustomError(
                message="Deleting of session was not acknowledged", code=500
            )

    def delete_project(self, project_id: str) -> CustomError | None:
        project = self.project_collection.find_one({"_id": ObjectId(project_id)})

        if not project:
            return CustomError(message="Project doesn't exist.", code=404)

        result = self.session_collection.update_many(
            filter={"project_id": project_id}, update={"$set": {"project_id": ""}}
        )

        if not result.acknowledged:
            return CustomError(
                message="Deleting of project was not acknowledged", code=500
            )

        project = self.project_collection.find_one_and_delete(
            {"_id": ObjectId(project_id)}
        )

        if not project:
            return CustomError(
                message="Deleting of project was not completed", code=500
            )

    def create_user(self, username: str) -> tuple[str, bool]:
        result = self.user_collection.insert_one(
            {
                "name": username,
                "memory": {},
            }
        )

        if not result.acknowledged:
            return "", False

        return str(result.inserted_id), True

    def fetch_user_id(self) -> tuple[str, str] | None:
        with self.user_collection.find(
            filter={}, projection={"memory": False}
        ) as cursor:
            user = list(cursor)
            if len(user) == 1:
                return str(user[0]["_id"]), user[0]["name"]
            return None

    def fetch_user(self, user_id: str) -> User | None:
        result = self.user_collection.find_one({"_id": ObjectId(user_id)})
        if result is not None:
            user: User = {
                "_id": str(result["_id"]),
                "name": result["name"],
                "memory": result["memory"],
            }
            return user
        return None

    def update_user_name(self, user_id: str, name: str) -> bool:
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {"name": name}}
        )

        return result.acknowledged

    def update_user_memory(self, user_id: str, key: str, value: Any) -> bool:
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {f"memory.{key}": value}}
        )
        return result.acknowledged

    def remove_user_memory(self, user_id: str, key: str) -> bool:
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$unset": {f"memory.{key}": ""}}
        )
        return result.acknowledged
