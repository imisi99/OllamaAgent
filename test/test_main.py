from typing import Any
from db.mongo import get_mongo_database
from main import app

from .test_mock import MockDatabase

db = MockDatabase()


def mock_db() -> Any:
    return db


app.dependency_overrides[get_mongo_database] = mock_db
