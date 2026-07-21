import json
from datetime import datetime, timedelta
from .mongo import Database

import redis

from schemas.mongo import Message

# TODO: It doesn't load previously existing chat when continuing


class Cache:
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
                err, messages = self.mongoDB.fetch_session_for_redis(session_id)
                if len(messages) > 0:
                    prev_messages = messages
                    new_memory = True

        if dont_preload:
            new_memory = True

        if prev_messages:
            if type(message) is Message:
                prev_messages.append(message)
            elif type(message) is list[Message]:
                prev_messages.extend(message)
        else:
            prev_messages = message

        self.client.rpush(session_id, json.dumps(prev_messages))

        expiry = (
            datetime.now() + timedelta(minutes=5)
            if new_memory
            else datetime.now() + timedelta(minutes=20)
        )

        self.client.expireat(session_id, expiry)

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
            self.add_short_term_memory(session[0]["_id"], session[1], dont_preload=True)

    def clear_all_memory(self):
        self.client.flushdb()
