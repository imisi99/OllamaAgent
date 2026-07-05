import base64
from datetime import datetime
import re
from typing import Any
from bson import ObjectId
from pymongo import MongoClient
from schemas.mongo import Audio, File, Image, Message, Session, User


class Database:
    def __init__(
        self, db: str, session: str, user: str, client: MongoClient[dict[str, Any]]
    ) -> None:
        self.db = db
        self.session = session
        self.user = user
        self.client = client
        self.session_collection = self.client[self.db][self.session]
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

    def create_session(self, session: Session) -> tuple[bool, str]:
        session["created_at"] = self.normalize_timestamp(session["created_at"])
        msg = session["messages"][0]
        msg_time = msg["timestamp"]
        msg["timestamp"] = self.normalize_timestamp(msg_time)
        self.normalize_image_files(msg["images"], msg["files"])
        self.normalize_audio(msg["audio"])
        result = self.session_collection.insert_one(
            {
                "uuid": session["uuid"],
                "name": session["name"],
                "created_at": session["created_at"],
                "messages": session["messages"],
            }
        )
        if not result.acknowledged:
            return False, ""

        return True, str(result.inserted_id)

    def fetch_session(self, session_id: str) -> Session | None:
        result = self.session_collection.find_one({"_id": ObjectId(session_id)})
        if result is not None:
            for msg in result["messages"]:
                self.denormalize_image_files(msg["images"], msg["files"])
                self.denormalize_audio(msg["audio"])
                msg["timestamp"] = self.denormalize_timestamp(msg["timestamp"])

            session: Session = {
                "_id": str(result["_id"]),
                "uuid": result["uuid"],
                "name": result["name"],
                "messages": result["messages"],
                "created_at": self.denormalize_timestamp(result["created_at"]),
            }

            return session
        return result

    def fetch_sessions(self, ids: list[str]) -> list[Session]:
        with self.session_collection.find(
            {"_id": [ObjectId(id) for id in ids]}
        ) as cursor:
            sessions = list(cursor)

        result: list[Session] = []
        for session in sessions:
            for msg in session["messages"]:
                self.denormalize_image_files(msg["images"], msg["files"])
                self.denormalize_audio(msg["audio"])
                msg["timestamp"] = self.denormalize_timestamp(msg["timestamp"])

            result.append(
                {
                    "_id": str(session["_id"]),
                    "uuid": session["uuid"],
                    "name": session["name"],
                    "created_at": self.denormalize_timestamp(session["created_at"]),
                    "messages": session["timestamp"],
                }
            )

        return result

    # TODO: Fetch in order of last message datetime && Also exclude the message resources
    def fetch_all_session_preview(self) -> list[Session]:
        with self.session_collection.find(filter={}, projection={}) as cursor:
            sessions = list(cursor)

        sessions.sort(
            key=lambda s: s["messages"][-1]["timestamp"]
            if s["messages"]
            else s["created_at"]
        )

        result: list[Session] = []
        for session in sessions:
            result.append(
                {
                    "_id": str(session["_id"]),
                    "uuid": session["uuid"],
                    "name": session["name"],
                    "created_at": self.denormalize_timestamp(session["created_at"]),
                    "messages": [],
                }
            )

        return result

    def fetch_all_session(self) -> list[Session]:
        with self.session_collection.find({}) as cursor:
            sessions = list(cursor)

        result: list[Session] = []
        for session in sessions:
            for msg in session["messages"]:
                self.denormalize_image_files(msg["images"], msg["files"])
                self.denormalize_audio(msg["audio"])
                msg["timestamp"] = self.denormalize_timestamp(msg["timestamp"])

            result.append(
                {
                    "_id": str(session["_id"]),
                    "uuid": session["uuid"],
                    "name": session["name"],
                    "created_at": self.denormalize_timestamp(session["created_at"]),
                    "messages": session["messages"],
                }
            )

        return result

    def fetch_session_for_redis(self, session_id: str) -> Session | None:
        result = self.session_collection.find_one(
            filter={"_id": ObjectId(session_id)},
            projection={
                "created_at": False,
                "messages.thought": False,
                "messages.files": False,
                "messages.timestamp": False,
            },
        )

        if result is None:
            return result

        for msg in result["messages"]:
            self.denormalize_audio(msg["audio"])
            self.denormalize_image_files(msg["images"], [])
            msg["timestamp"] = ""
            msg["files"] = []
            msg["thought"] = ""

        session = Session(
            {
                "messages": result["messages"],
                "_id": session_id,
                "created_at": "",
                "name": result["name"],
                "uuid": result["uuid"],
            }
        )

        return session

    def fetch_all_session_for_redis(self) -> list[Session]:
        with self.session_collection.find(
            filter={},
            projection={
                "created_at": False,
                "messages.thought": False,
                "messages.files": False,
                "messages.timestamp": False,
            },
        ) as cursor:
            sessions = list(cursor)

        result: list[Session] = []
        for session in sessions:
            for msg in session["messages"]:
                self.denormalize_audio(msg["audio"])
                self.denormalize_image_files(msg["images"], [])
                msg["timestamp"] = ""
                msg["files"] = []
                msg["thought"] = ""

            result.append(
                Session(
                    {
                        "_id": str(session["_id"]),
                        "uuid": session["uuid"],
                        "created_at": "",
                        "name": session["name"],
                        "messages": session["messages"],
                    }
                )
            )

        return result

    def rename_session(self, session_id: str, name: str) -> bool:
        result = self.session_collection.update_one(
            {"_id": ObjectId(session_id)}, {"$set": {"name": name}}
        )

        return result.acknowledged

    def add_messages(self, session_id: str, message: Message) -> bool:
        self.normalize_image_files(message["images"], message["files"])
        self.normalize_audio(message["audio"])
        message["timestamp"] = self.normalize_timestamp(message["timestamp"])
        result = self.session_collection.update_one(
            {"_id": ObjectId(session_id)}, {"$push": {"messages": message}}
        )

        return result.acknowledged

    def delete_session(self, session_id: str) -> bool:
        result = self.session_collection.delete_one({"_id": ObjectId(session_id)})

        return result.acknowledged

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

        if result.modified_count == 0:
            return False

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
