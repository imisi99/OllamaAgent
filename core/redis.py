import json
from datetime import datetime, timedelta
from .mongo import Database

import redis
from schemas.mongo import Message

# TODO: It doesn't load previously existing chat when continuing


class Redis:
    def __init__(self, client: redis.Redis, mongoDB: Database) -> None:
        self.client = client
        self.mongoDB = mongoDB

    def has_short_term_memory(self, session_id: str) -> bool:
        return bool(self.client.exists(session_id))

    def add_short_term_memory(
        self,
        session_id: str,
        message: Message | list[Message],
        dont_preload: bool = False,
    ):
        prev_messages = None
        new_memory = False
        if not dont_preload:
            if not self.has_short_term_memory(session_id):
                session = self.mongoDB.fetch_session_for_redis(session_id)
                if session is not None:
                    prev_messages = session["messages"]
                    new_memory = True

        if dont_preload:
            new_memory = True

        if type(message) is Message:
            if prev_messages is not None:
                prev_messages.append(message)
        else:
            prev_messages = message

        self.client.rpush(session_id, json.dumps(prev_messages))

        new_expiry = datetime.now() + timedelta(minutes=5)
        existing_expiry = datetime.now() + timedelta(minutes=20)

        if new_memory:
            self.client.expireat(session_id, new_expiry)
        else:
            self.client.expireat(session_id, existing_expiry)

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
        sessions = self.mongoDB.fetch_all_session_for_redis()
        for session in sessions:
            self.add_short_term_memory(
                session["_id"], session["messages"], dont_preload=True
            )
            self.client.expireat(
                session["_id"], datetime.now() + timedelta(minutes=10), nx=True
            )

    def clear_all_memory(self):
        self.client.flushdb()
