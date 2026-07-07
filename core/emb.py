import json
from langchain_ollama import OllamaEmbeddings
from typing import Optional

from schemas.mongo import Session
from .agent import Model
# TODO: Work on the excedding limit for the update (a newer model ? )


class EmbeddingModel:
    def __init__(self, emb_model: OllamaEmbeddings, model: Model) -> None:
        self.EMB_MODEL = emb_model
        self.model = model

    async def generate_vector_embedding(self, session: Session) -> list[float]:
        info = {}
        if len(session["messages"]) >= 4:
            info["message"] = self.model.summarize_messages(session["messages"])
        else:
            info["message"] = [{"msg": msg["content"]} for msg in session["messages"]]
        text = json.dumps(info)
        vector = await self.EMB_MODEL.aembed_query(text)
        return vector

    async def generate_vector_embedding_query(self, query: str) -> list[float]:
        vector = await self.EMB_MODEL.aembed_query(query)
        return vector


EMB_MODEL: Optional[EmbeddingModel] = None


def create_emb_model(emb_model: OllamaEmbeddings) -> EmbeddingModel:
    model = EmbeddingModel(emb_model)
    return model


def get_emb_model() -> EmbeddingModel:
    if EMB_MODEL is None:
        raise RuntimeError("[EMB_MODEL] Embedding Model is not initialized")
    return EMB_MODEL
