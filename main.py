import asyncio
import logging
import os
import httpx
from langchain_ollama import ChatOllama, OllamaEmbeddings
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.tools import tools
from core.prompt import system_prompt
from db import mongo, qdrant, redis
from core import agent, emb
from app.server import serve
from app.session import session

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for app"""
    try:
        qdrant.QDRANT_CLIENT = qdrant.connect_qdrant()
        qdrant.ensure_collections()
        mongo.MONGO_CLIENT = mongo.connect_mongo()
        redis.REDIS_CLIENT = redis.connect_redis()

        mongo.MONGO_DATABASE = mongo.create_mongo_database()
        qdrant.QDRANT_DATABASE = qdrant.create_qdrant_database(emb.get_emb_model())
        redis.REDIS_DATABASE = redis.create_redis_database(
            redis.REDIS_CLIENT, mongo.MONGO_DATABASE
        )
        redis.REDIS_DATABASE.populate_cache()

        OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")

        agent.LLM = ChatOllama(
            model="qwen3.5:4b",
            base_url=OLLAMA_BASE_URL,
            keep_alive=-1,
            reasoning=True,
            verbose=True,
        )
        agent.LLM_NO_REASONING = ChatOllama(
            model="qwen3.5:4b",
            base_url=OLLAMA_BASE_URL,
            keep_alive=-1,
            reasoning=False,
            verbose=True,
        )
        embed = OllamaEmbeddings(
            model="nomic-embed-text", base_url=OLLAMA_BASE_URL, keep_alive=-1
        )
        emb.EMB_MODEL = emb.create_emb_model(embed)
        agent_graph = agent.build_agent(agent.LLM, tools, system_prompt)
        agent.GRAPH = agent.build_graph(agent_graph)

        worker = asyncio.create_task(qdrant.QDRANT_DATABASE.worker())

    except Exception as e:
        logging.error(
            "An error occured while trying startup app -> %s", e, exc_info=True
        )
        raise RuntimeError("")
    yield
    async with httpx.AsyncClient() as client:
        base_url = os.getenv("OLLAMA_BASE_URL", "")
        await client.post(
            f"{base_url}/api/chat",
            json={"model": "qwen3.5:4b", "keep_alive": 0},
        )

        await client.post(
            f"{base_url}/api/embeddings",
            json={"model": "nomic-embed-text", "keep_alive": 0},
        )
    await (
        qdrant.QDRANT_DATABASE.finish_queue()
    ) if qdrant.QDRANT_DATABASE is not None else None
    worker.cancel()
    try:
        await worker
    except asyncio.CancelledError:
        pass
    redis.REDIS_DATABASE.clear_all_memory() if redis.REDIS_DATABASE is not None else None
    qdrant.QDRANT_CLIENT.close() if qdrant.QDRANT_CLIENT is not None else None
    mongo.MONGO_CLIENT.close() if mongo.MONGO_CLIENT is not None else None
    redis.REDIS_CLIENT.close() if redis.REDIS_CLIENT is not None else None


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(session)
app.include_router(serve)
