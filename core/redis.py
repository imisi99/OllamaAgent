from datetime import datetime
from db import redis


def add_long_term_memory(value: str):
    redis.get_redis_client().hset(
        name="memory", key=datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), value=value
    )


def view_long_term_memory():
    redis.get_redis_client().hscan(name="memory")
