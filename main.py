import logging
import os
import httpx
from langchain_ollama import ChatOllama
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.tools import tools
from core.prompt import system_prompt
from db import mongo, qdrant, redis
from core import agent
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

        OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")

        agent.LLM = ChatOllama(
            model="qwen2.5-coder",
            base_url=OLLAMA_BASE_URL,
            reasoning=True,
            keep_alive="-1",
        )
        agent_graph = agent.build_agent(agent.LLM, tools, system_prompt)
        agent.GRAPH = agent.build_graph(agent_graph)

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
            json={"model": "qwen2.5-coder", "keep_alive": 0},
        )
    qdrant.QDRANT_CLIENT.close() if qdrant.QDRANT_CLIENT is not None else qdrant.QDRANT_CLIENT
    mongo.MONGO_CLIENT.close() if mongo.MONGO_CLIENT is not None else mongo.MONGO_CLIENT
    redis.REDIS_CLIENT.close() if redis.REDIS_CLIENT is not None else redis.REDIS_CLIENT


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(session)
app.include_router(serve)
