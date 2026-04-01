import json
from datetime import datetime, timedelta
from typing import Union

import redis
from schemas.mongo import Message


class Redis:
    def __init__(self, client: redis.Redis) -> None:
        self.client = client

    def add_short_term_memory(
        self,
        session_id: str,
        message: Union[Message, list[Message]],
    ):
        self.client.rpush(session_id, json.dumps(message))
        expiry = datetime.now() + timedelta(minutes=10)
        self.client.expireat(session_id, expiry, gt=True)

    def get_short_term_memory(self, session_id: str) -> list[Message]:
        msg = self.client.lrange(session_id, 0, -1)

        if isinstance(msg, list):
            return [json.loads(m) for m in msg]
        else:
            raise RuntimeError("Got an async response expected sync redis client")

    def clear_short_term_memory(self, session_id: str):
        self.client.delete(session_id)

    def clear_all_memory(self):
        self.client.flushdb()
