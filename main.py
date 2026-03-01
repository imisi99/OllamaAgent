import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from db import mongo, qdrant, redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for app"""
    try:
        qdrant.QDRANT_CLIENT = qdrant.connect_qdrant()
        qdrant.ensure_collections()
        mongo.MONGO_CLIENT = mongo.connect_mongo()
        mongo.ensure_collections()
        redis.REDIS_CLIENT = redis.connect_redis()

    except Exception as e:
        logging.error("An error occured while trying startup app -> %s", e)
    yield
    qdrant.QDRANT_CLIENT
    mongo.MONGO_CLIENT.close() if mongo.MONGO_CLIENT is not None else mongo.MONGO_CLIENT
    redis.REDIS_CLIENT


app = FastAPI(lifespan=lifespan)
