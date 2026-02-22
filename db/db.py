import logging
import os
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

QDRANT_CLIENT: Optional[QdrantClient] = None
VECTORSIZE = 768
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "0"))


def connect_qdrant() -> QdrantClient:
    """Connects and returns a qdrant connection client"""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return client


def ensure_collections(client: QdrantClient):
    collections = client.get_collections().collections
    existing = {c.name for c in collections}

    if "projects" not in existing:
        logging.info("[QDRANT] Creating the projects collection  as it didn't exist.")
        try:
            client.create_collection(
                collection_name="projects",
                vectors_config={
                    "readme": VectorParams(
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
