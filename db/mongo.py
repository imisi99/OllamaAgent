import os
from typing import Optional
from pymongo import MongoClient
from datetime import datetime


MONGO_CLIENT: Optional[MongoClient] = None
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT", "0"))


def connect_mongo() -> MongoClient:
    """Connects and returns a mongo connection client"""
    client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    return client


def get_mongo_client() -> MongoClient:
    """Returns a pre-initialized mongo client"""
    if MONGO_CLIENT is None:
        raise RuntimeError("Mongo client is not initialized.")
    return MONGO_CLIENT
