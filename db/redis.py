import os
from typing import Optional
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", "0"))
REDIS_CLIENT: Optional[redis.Redis] = None


def connect_redis() -> redis.Redis:
    """Connect and returns a redis connection client"""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    return client


def get_redis_client() -> redis.Redis:
    """Returns a pre-initialized redis client"""
    if REDIS_CLIENT is None:
        raise RuntimeError("Redis client is not initialized")
    return REDIS_CLIENT
