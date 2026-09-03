import json
from langchain_ollama import OllamaEmbeddings
from typing import Optional


from core.cache import Cache
from schemas.qdrant import QSession


class EmbeddingModel:
    def __init__(self, emb_model: OllamaEmbeddings, cache: Cache) -> None:
        self.EMB_MODEL = emb_model
        self.cache = cache

    async def generate_vector_embedding(self, session: QSession) -> list[float]:
        info = {}

        if len(session.messages) >= 4 == 0:
            info["message"] = self.cache.get_summary(session.id)
        else:
            info["message"] = [{"msg": msg.content} for msg in session.messages]

        text = json.dumps(info)
        vector = await self.EMB_MODEL.aembed_query(text)

        return vector

    async def generate_vector_embedding_query(self, query: str) -> list[float]:
        vector = await self.EMB_MODEL.aembed_query(query)
        return vector


EMB_MODEL: Optional[EmbeddingModel] = None


def create_emb_model(emb_model: OllamaEmbeddings, cache: Cache) -> EmbeddingModel:
    new_model = EmbeddingModel(emb_model, cache)
    return new_model


def get_emb_model() -> EmbeddingModel:
    if EMB_MODEL is None:
        raise RuntimeError("[EMB_MODEL] Embedding Model is not initialized")
    return EMB_MODEL
