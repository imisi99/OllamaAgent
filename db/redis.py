import os
from typing import Optional
import redis

from core.redis import Redis

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "0"))
REDIS_PASS = os.getenv("REDIS_PASS", "")
REDIS_CLIENT: Optional[redis.Redis] = None
REDIS_DATABASE: Optional[Redis] = None


def connect_redis() -> redis.Redis:
    """Connect and returns a redis connection client"""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS)
    return client


def get_redis_client() -> redis.Redis:
    """Returns a pre-initialized redis client"""
    if REDIS_CLIENT is None:
        raise RuntimeError("Redis client is not initialized")
    return REDIS_CLIENT


def create_redis_database(client: redis.Redis) -> Redis:
    cache = Redis(client)
    return cache


def get_redis_database() -> Redis:
    if REDIS_DATABASE is None:
        raise RuntimeError("[REDIS] Redis cache is not initialized")
    return REDIS_DATABASE
