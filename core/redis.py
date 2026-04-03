import json
from datetime import datetime, timedelta
from typing import Union
from .mongo import Database

import redis
from schemas.mongo import Message


class Redis:
    def __init__(self, client: redis.Redis, mongoDB: Database) -> None:
        self.client = client
        self.mongoDB = mongoDB

    def has_short_term_memory(self, session_id: str) -> bool:
        return bool(self.client.exists(session_id))

    def add_short_term_memory(
        self,
        session_id: str,
        message: Union[Message, list[Message]],
        preload: bool = False,
    ):
        prev_messages = None
        if not preload:
            if not self.has_short_term_memory(session_id):
                session = self.mongoDB.fetch_session(session_id)
                if session is not None:
                    prev_messages = session["messages"]

        if prev_messages is not None:
            if type(message) is Message:
                prev_messages.append(message)
        else:
            prev_messages = message

        self.client.rpush(session_id, json.dumps(prev_messages))
        expiry = datetime.now() + timedelta(minutes=20)
        self.client.expireat(session_id, expiry, gt=True)

    def get_short_term_memory(self, session_id: str) -> list[Message]:
        raw = self.client.lrange(session_id, 0, -1)
        if not isinstance(raw, list):
            raise RuntimeError("Got an async response, expected sync response")

        messages: list[Message] = []
        for msg in raw:
            parsed = json.loads(msg)
            if isinstance(parsed, list):
                messages.extend(parsed)
            else:
                messages.append(parsed)
        return messages

    def clear_short_term_memory(self, session_id: str):
        self.client.delete(session_id)

    def populate_cache(self):
        sessions = self.mongoDB.fetch_all_session()
        for session in sessions:
            self.add_short_term_memory(
                session["_id"], session["messages"], preload=True
            )

    def clear_all_memory(self):
        self.client.flushdb()
