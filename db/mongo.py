import os
from typing import Dict, Optional, Any
from pymongo import MongoClient

from schemas.mongo import Session, User


MONGO_CLIENT: Optional[MongoClient[Dict[str, Any]]] = None
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
DB_NAME = "agent"
SESSISON = "sessions"
USER = "user"


def connect_mongo() -> MongoClient[Session]:
    """Connects and returns a mongo connection client"""
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")
    uri = f"mongodb://{username}:{password}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

    client = MongoClient(uri)
    return client


def ensure_collections():
    try:
        database = get_mongo_client()[DB_NAME]
        if SESSISON not in database.list_collection_names():
            database.create_collection(SESSISON)
    except Exception as e:
        raise RuntimeError(
            f"[MONGO] An error occured while trying to create a collection -> {e}"
        )


def get_mongo_client() -> MongoClient[Dict[str, Any]]:
    """Returns a pre-initialized mongo client"""
    if MONGO_CLIENT is None:
        raise RuntimeError("[MONGO] Mongo client is not initialized.")
    return MONGO_CLIENT
