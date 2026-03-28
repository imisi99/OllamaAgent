import json
from datetime import datetime, timedelta
from db.redis import get_redis_client
from schemas.mongo import Message


class Redis:
    def add_short_term_memory(self, session_id: str, message: Message):
        client = get_redis_client()
        client.rpush(session_id, json.dumps(message))
        expiry = datetime.now() + timedelta(minutes=10)
        client.expireat(session_id, expiry, gt=True)

    def get_short_term_memory(self, session_id: str) -> list[Message]:
        msg = get_redis_client().lrange(session_id, 0, -1)

        if isinstance(msg, list):
            return [json.loads(m) for m in msg]
        else:
            raise RuntimeError("Got an async response expected sync redis client")

    def clear_short_term_memory(self, session_id: str):
        get_redis_client().delete(session_id)

    def clear_all_memory(self):
        get_redis_client()
