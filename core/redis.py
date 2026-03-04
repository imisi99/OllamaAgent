import json
from db import redis
from models.mongo import Message


def add_short_term_memory(session_id: str, message: Message):
    redis.get_redis_client().rpush(session_id, json.dumps(message))


def get_short_term_memory(session_id: str) -> list[Message]:
    msg = redis.get_redis_client().lrange(session_id, 0, -1)

    if isinstance(msg, list):
        return [json.loads(m) for m in msg]
    else:
        raise RuntimeError("Got an async response expected sync redis client")


def clear_short_term_memory(session_id: str):
    redis.get_redis_client().delete(session_id)
