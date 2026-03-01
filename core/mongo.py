from bson import ObjectId
from db.mongo import DB_NAME, SESSISON, get_mongo_client
from models.mongo import Message, Session

db_name = "agent"
session_collection = "sessions"


def create_session(session: Session) -> tuple[bool, str]:
    client = get_mongo_client()
    database = client[DB_NAME]
    collection = database[SESSISON]

    result = collection.insert_one(session)
    if not result.acknowledged:
        return False, ""

    return True, str(result.inserted_id)


def fetch_session(session_id: str) -> Session | None:
    client = get_mongo_client()
    database = client[DB_NAME]
    collection = database[SESSISON]

    result = collection.find_one({"_id": ObjectId(session_id)})
    return result


def fetch_all_session() -> list[Session] | None:
    client = get_mongo_client()
    database = client[DB_NAME]
    collection = database[SESSISON]

    sessions = []

    with collection.find() as cursor:
        for doc in cursor:
            sessions.append(doc)

    return sessions


def add_messages(session_id: str, message: Message) -> bool:
    client = get_mongo_client()
    database = client[DB_NAME]
    collection = database[SESSISON]

    result = collection.update_one(
        {"_id": ObjectId(session_id)}, {"$push": {"messages": message}}
    )

    return result.acknowledged


def delete_session(session_id: str) -> bool:
    client = get_mongo_client()
    database = client[DB_NAME]
    collection = database[SESSISON]

    result = collection.delete_one({"_id": ObjectId(session_id)})

    return result.acknowledged
