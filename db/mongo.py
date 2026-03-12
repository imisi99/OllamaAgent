import os
from typing import Dict, Optional, Any
from pymongo import MongoClient

from core.mongo import Database
from schemas.mongo import Session


MONGO_CLIENT: Optional[MongoClient[Dict[str, Any]]] = None
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
DB_NAME = "agent"
SESSISON = "sessions"
USER = "user"
MONGO_DATABASE: Optional[Database] = None


def connect_mongo() -> MongoClient[Session]:
    """Connects and returns a mongo connection client"""
    username = os.getenv("MONGO_USERNAME")
    password = os.getenv("MONGO_PASSWORD")
    uri = f"mongodb://{username}:{password}@{MONGO_HOST}:{MONGO_PORT}/?authSource=admin"

    client = MongoClient(uri)
    return client


def get_mongo_client() -> MongoClient[Dict[str, Any]]:
    """Returns a pre-initialized mongo client"""
    if MONGO_CLIENT is None:
        raise RuntimeError("[MONGO] Mongo client is not initialized.")
    return MONGO_CLIENT


def create_mongo_database() -> Database:
    database = Database(DB_NAME, SESSISON, USER, get_mongo_client())
    return database


def get_mongo_database() -> Database:
    if MONGO_DATABASE is None:
        raise RuntimeError("[MONGO] Mongo database is not initialized.")
    return MONGO_DATABASE
