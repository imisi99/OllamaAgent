from datetime import datetime
from mongoengine import (
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    IntField,
    StringField,
    ListField,
)


class Message(EmbeddedDocument):
    idx = IntField(required=True)
    role = StringField(required=True)
    content = StringField(required=True)
    timestamp = DateTimeField(default=datetime.now())


class Session(Document):
    session_name = StringField(unique=True, required=True)
    created_at = DateTimeField(default=datetime.now())
    messages = ListField(EmbeddedDocumentField(Message))  # type: ignore

    meta = {"collection": "sessions"}
