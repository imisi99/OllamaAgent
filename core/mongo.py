from typing import Any, cast
from bson import ObjectId
from pymongo import MongoClient
from schemas.mongo import Message, Session, User


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

    def create_session(self, session: Session) -> tuple[bool, str]:
        result = self.session_collection.insert_one(
            {
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
            if not all(k in result for k in ("name", "created_at", "messages")):
                return None
            return cast(Session, result)
        return None

    def fetch_all_session(self) -> list[Session] | None:
        sessions = []

        with self.session_collection.find() as cursor:
            for doc in cursor:
                sessions.append(doc)

        return sessions

    def add_messages(self, session_id: str, message: Message) -> bool:
        result = self.session_collection.update_one(
            {"_id": ObjectId(session_id)}, {"$push": {"messages": message}}
        )

        return result.acknowledged

    def delete_session(self, session_id: str) -> bool:
        result = self.session_collection.delete_one({"_id": ObjectId(session_id)})

        return result.acknowledged

    def fetch_user(self, user_id: str) -> User | None:
        result = self.user_collection.find_one({"_id": ObjectId(user_id)})
        if result is not None:
            if not all(k in result for k in ("name", "memory")):
                return None
            return cast(User, result)

        return None

    def update_user_memory(self, user_id: str, key: str, value: Any) -> bool:
        result = self.user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": {f"memory.{key}": value}}
        )

        return result.acknowledged
