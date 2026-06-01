import asyncio
import logging
import os
import requests
from langchain_ollama import ChatOllama, OllamaEmbeddings
from contextlib import asynccontextmanager
from fastapi import FastAPI
from faster_whisper import WhisperModel, download_model
from core import audio
from core.audio import create_audio_model
from core.tools import tools
from core.prompt import system_prompt
from db import mongo, qdrant, redis
from core import agent, emb
from app.server import serve
from app.session import session
from app.user import user

logging.basicConfig(level=logging.INFO)


# TODO:
# A clickable icon that can open the site (and also startup the app itself a scipt ?).
# Create and use a different model for the qdrant and redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for app"""
    try:
        qdrant.QDRANT_CLIENT = qdrant.connect_qdrant()
        qdrant.ensure_collections()
        mongo.MONGO_CLIENT = mongo.connect_mongo()
        redis.REDIS_CLIENT = redis.connect_redis()

        mongo.MONGO_DATABASE = mongo.create_mongo_database()
        redis.REDIS_DATABASE = redis.create_redis_database(
            redis.REDIS_CLIENT, mongo.MONGO_DATABASE
        )
        redis.REDIS_DATABASE.populate_cache()

        OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")

        reason = ChatOllama(
            model="qwen3.5:4b",
            base_url=OLLAMA_BASE_URL,
            keep_alive=-1,
            reasoning=True,
            verbose=True,
        )
        no_reason = ChatOllama(
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
        qdrant.QDRANT_DATABASE = qdrant.create_qdrant_database(emb.get_emb_model())

        agent.MODEL = agent.create_model(
            no_reason, reason, tools, system_prompt, qdrant.QDRANT_DATABASE
        )
        worker = asyncio.create_task(qdrant.QDRANT_DATABASE.worker())

        try:
            model_dir = download_model(
                "base",
                output_dir="./models",
                local_files_only=True,
            )

        except Exception as e:
            logging.info(
                f"Falling to downloading of audio model cause the model did not exist locally -> {e}"
            )
            model_dir = download_model("base", output_dir="./models")

        audio.AUDIO_MODEL = create_audio_model(model_dir)

    except Exception as e:
        logging.error(
            f"An error occured while trying startup app -> {e}", exc_info=True
        )
        raise RuntimeError(f"Failed to startup app -> {e}")
    yield
    base_url = os.getenv("OLLAMA_BASE_URL", "")
    requests.post(
        url=f"{base_url}/api/chat", json={"model": "qwen3.5:4b", "keep_alive": 0}
    )
    requests.post(
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
app.include_router(user)
