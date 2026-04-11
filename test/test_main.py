from typing import Any
from core.agent import get_model
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from main import app

from .test_mock import MockDatabase, MockLLM, MockQdrant

db = MockDatabase()
qdb = MockQdrant()
model = MockLLM()


def mock_db() -> Any:
    return db


def mock_qdb() -> Any:
    return qdb


def mock_model() -> Any:
    return model


app.dependency_overrides[get_mongo_database] = mock_db
app.dependency_overrides[get_qdrant_database] = mock_qdb
app.dependency_overrides[get_model] = mock_model
