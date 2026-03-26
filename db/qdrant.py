import logging
import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from core.emb import EmbeddingModel
from core.qdrant import Qdrant

QDRANT_CLIENT: Optional[QdrantClient] = None
VECTORSIZE = 768
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "0"))
QDRANT_DATABASE: Optional[Qdrant] = None


def connect_qdrant() -> QdrantClient:
    """Connects and returns a qdrant connection client"""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return client


def ensure_collections():
    collections = get_qdrant_client().get_collections().collections
    existing = {c.name for c in collections}

    if "chats" not in existing:
        logging.info("[QDRANT] Creating the projects collection as it didn't exist.")
        try:
            get_qdrant_client().create_collection(
                collection_name="chats",
                vectors_config={
                    "messages": VectorParams(
                        size=VECTORSIZE, distance=Distance.COSINE
                    )  # Might have to add some other vector later on
                },
            )

            logging.info("[QDRANT] Projects collection created.")
        except Exception as e:
            logging.error("[QDRANT] Failed to create the projects collection -> %s", e)
            raise


def get_qdrant_client() -> QdrantClient:
    """Returns a pre-initialized qdrant client"""
    if QDRANT_CLIENT is None:
        raise RuntimeError("Qdrant client is not initialized.")
    return QDRANT_CLIENT


def create_qdrant_database(embedding: EmbeddingModel) -> Qdrant:
    database = Qdrant(get_qdrant_client(), embedding)
    return database


def get_qdrant_database() -> Qdrant:
    if QDRANT_DATABASE is None:
        raise RuntimeError("[QDRANT] Qdrant database is not initialized")
    return QDRANT_DATABASE
