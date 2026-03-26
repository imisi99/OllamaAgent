import json
import os
from typing import Optional
import requests

from schemas.mongo import Session


class EmbeddingModel:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "")

    def generate_vector_embedding(self, session: Session) -> list[float]:
        response = requests.post(
            self.base_url,
            json={"model": "nomic-embed-text", "prompt": json.dumps(session)},
        )
        response.raise_for_status()
        return response.json()["embedding"]

    def generate_vector_embedding_query(self, query: str) -> list[float]:
        response = requests.post(
            self.base_url, json={"model": "nomic-embed-text", "prompt": query}
        )
        response.raise_for_status()
        return response.json()["embedding"]


EMB_MODEL: Optional[EmbeddingModel] = None


def create_emb_model() -> EmbeddingModel:
    model = EmbeddingModel()
    return model


def get_emb_model() -> EmbeddingModel:
    if EMB_MODEL is None:
        raise RuntimeError("[EMB_MODEL] Embedding Model is not initialized")
    return EMB_MODEL
