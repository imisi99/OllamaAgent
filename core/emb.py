import json
from langchain_ollama import OllamaEmbeddings
from typing import Optional


from core import agent
from schemas.qdrant import QSession

# TODO: Work on the summarizer not calling on every turn after reaching the point for calling


class EmbeddingModel:
    def __init__(self, emb_model: OllamaEmbeddings) -> None:
        self.EMB_MODEL = emb_model

    async def generate_vector_embedding(self, session: QSession) -> list[float]:
        info = {}

        if len(session.messages) >= 4:
            info["message"] = await agent.get_model().summarize_messages(
                session.messages
            )
        else:
            info["message"] = [{"msg": msg.content} for msg in session.messages]

        text = json.dumps(info)
        vector = await self.EMB_MODEL.aembed_query(text)

        return vector

    async def generate_vector_embedding_query(self, query: str) -> list[float]:
        vector = await self.EMB_MODEL.aembed_query(query)
        return vector


EMB_MODEL: Optional[EmbeddingModel] = None


def create_emb_model(emb_model: OllamaEmbeddings) -> EmbeddingModel:
    new_model = EmbeddingModel(emb_model)
    return new_model


def get_emb_model() -> EmbeddingModel:
    if EMB_MODEL is None:
        raise RuntimeError("[EMB_MODEL] Embedding Model is not initialized")
    return EMB_MODEL
