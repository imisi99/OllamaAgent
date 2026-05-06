import asyncio
import logging
from datetime import datetime
from enum import Enum
import time
from typing import Union, cast
from uuid import uuid4
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)
from qdrant_client.http.models import UpdateStatus
from .emb import EmbeddingModel
from schemas.mongo import Message, Session


class Job(str, Enum):
    CREATE_POINT = "create point"
    UPDATE_POINT = "update point"
    UPDATE_PAYLOAD = "update payload"
    DELETE_POINT = "delete point"


class Task:
    def __init__(
        self,
        job: Job,
        uid: str = "",
        name: str = "",
        session: Union[Session, None] = None,
        message: Union[Message, None] = None,
        retries: int = 3,
    ) -> None:
        self.uid = uid
        self.job = job
        self.name = name
        self.session = session
        self.message = message
        self.retries = retries


class Qdrant:
    def __init__(self, client: QdrantClient, embedding: EmbeddingModel) -> None:
        self.client = client
        self.embedding = embedding
        self.jobs: asyncio.Queue[Task] = asyncio.Queue()

    def normalize_created_at(self, timestamp: datetime | str) -> str:
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        return timestamp

    async def create_point(self, session: Session) -> bool:
        session["created_at"] = self.normalize_created_at(session["created_at"])
        vector = await self.embedding.generate_vector_embedding(session)
        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=session["uuid"],
                    vector={"messages": vector},
                    payload={
                        "_id": session["_id"],
                        "uuid": session["uuid"],
                        "name": session["name"],
                        "messages": session["messages"],
                        "created_at": session["created_at"],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to create session with id -> {session['uuid']} result -> {result}"
            )
        return success

    async def get_related_points(
        self,
        id: str,
        query: str = "",
        score_threshold: float = 0.5,
        use_query: bool = False,
        limit: int = 5,
    ) -> tuple[list[tuple[Session, float]], float] | None:
        vector = None
        if use_query:
            vector = await self.embedding.generate_vector_embedding_query(query)
        else:
            point = self.client.retrieve(
                collection_name="chats", ids=[id], with_vectors=True
            )

            if not point:
                logging.error(
                    f"Tried to find related points with id -> {id} but point doesn't exist in vector space."
                )
                return None

            vector = point[0].vector
            if vector is None:
                logging.error(
                    f"Tried to find related points with id -> {id} but point doesn't have a vector component"
                )
                return None

            if isinstance(vector, dict):
                vector = vector.get("messages")
                if vector is None:
                    logging.error(
                        f"Tried to find related points with id -> {id} but point doesn't have a message vector component"
                    )
                    return None

        result = self.client.query_points(
            collection_name="chats",
            query=vector,
            using="messages",
            score_threshold=score_threshold,
            limit=limit,
            query_filter=Filter(
                must_not=[FieldCondition(key="uuid", match=MatchValue(value=id))]
            ),
        )

        if len(result.points) == 0:
            return None

        response: list[tuple[Session, float]] = []
        avgScore = 0
        for point in result.points:
            if point.payload:
                point.payload["created_at"] = datetime.fromisoformat(
                    point.payload["created_at"]
                )
                payload = cast(Session, point.payload)
                response.append((payload, point.score))
                avgScore += point.score

        avgScore /= len(response) if len(response) > 0 else 1
        logging.info(f"Recommended {len(response)} with an average score of {avgScore}")
        return response, avgScore

    async def update_point(self, id: str, message: Message) -> bool:
        point = self.client.retrieve("chats", ids=[id], with_payload=True)
        if not point:
            logging.error(
                f"Tried to update point with id -> {id} but point doesn't exist in vector space."
            )
            return False

        payload = point[0].payload
        if not payload:
            logging.error(
                f"Tried to update point with id -> {id} but payload doesn't exist"
            )
            return False

        session = cast(Session, payload)
        session["messages"].append(message)

        vector = await self.embedding.generate_vector_embedding(session)
        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=id,
                    vector={"messages": vector},
                    payload={
                        "_id": session["_id"],
                        "uuid": session["uuid"],
                        "name": session["name"],
                        "messages": session["messages"],
                        "created_at": session["created_at"],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to update session with id -> {id} result -> {result}, status -> {result.status}"
            )
        return success

    async def update_payload(self, id: str, name: str) -> bool:
        point = self.client.retrieve(
            collection_name="chats", ids=[id], with_payload=False
        )

        if not point:
            logging.error(
                f"Tried to update payload with point id -> {id} but point doesn't exist in vector space."
            )
            return False

        result = self.client.set_payload(
            collection_name="chats", payload={"name": name}, points=[id]
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to update the title of point with id -> {id} result -> {result}"
            )
        return success

    async def delete_point(self, id: str) -> bool:
        point = self.client.retrieve(
            collection_name="chats", ids=[id], with_payload=False
        )

        if not point:
            logging.error(
                f"Tried to delete point with id -> {id} but point doesn't exist in vector space."
            )
            return False

        result = self.client.delete(collection_name="chats", points_selector=[id])

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(f"Failed to delete point with id -> {id} result -> {result}")
        return success

    async def embed_chunks(self, session_id: str, chunks: list[Document]) -> bool:
        points = []
        for chunk in chunks:
            vector = await self.embedding.generate_vector_embedding_query(
                chunk.page_content
            )
            points.append(
                PointStruct(
                    id=str(uuid4()),
                    vector={"files": vector},
                    payload={
                        "session_id": session_id,
                        "text": chunk.page_content,
                        "source": chunk.metadata.get("filename", ""),
                        "page": chunk.metadata.get("page", None),
                    },
                )
            )

        created = self.client.upsert(collection_name="chats", points=points)

        success = created.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to create chunk point for session -> {session_id} result -> {created}"
            )
        return success

    async def retrieve_file_chunks(
        self,
        query: str,
        sess_uid: str,
        k: int = 6,
    ) -> list[str]:
        vector = await self.embedding.generate_vector_embedding_query(query)

        result = self.client.query_points(
            collection_name="chats",
            query=vector,
            using="files",
            limit=k,
            query_filter=Filter(
                must=[
                    FieldCondition(key="session_id", match=MatchValue(value=sess_uid))
                ]
            ),
        )

        chunks: list[str] = []
        score = 0
        for point in result.points:
            score += point.score
            if point.payload is not None:
                chunks.append(
                    f"RETRIEVED CONTEXT: {point.payload['text']} \n SOURCE: {point.payload['source']} \n PAGE_NO: {point.payload['page']}"
                )

        logging.info(
            f"Retrieved chunks with an average score of {score if len(result.points) == 0 else score / len(result.points)}"
        )

        return chunks

    def add_job(self, task: Task):
        self.jobs.put_nowait(task)

    async def worker(self):
        MAX_ATTEMPTS = 3
        while True:
            task = None
            try:
                task = await self.jobs.get()
                for attempts in range(task.retries):
                    try:
                        match task.job:
                            case Job.CREATE_POINT:
                                created = await self.create_point(
                                    cast(Session, task.session)
                                )
                                if created:
                                    break
                            case Job.UPDATE_POINT:
                                updated = await self.update_point(
                                    task.uid, cast(Message, task.message)
                                )
                                if updated:
                                    break
                            case Job.DELETE_POINT:
                                deleted = await self.delete_point(task.uid)
                                if deleted:
                                    break
                            case Job.UPDATE_PAYLOAD:
                                updated = await self.update_payload(task.uid, task.name)
                                if updated:
                                    break
                    except Exception as e:
                        if attempts < MAX_ATTEMPTS - 1:
                            logging.error(
                                f"[qdrant worker] attempt {attempts + 1} failed running job -> {task.job.value}, retrying... error -> {e}"
                            )
                            await asyncio.sleep(1.5 * attempts)
                        else:
                            logging.error(
                                f"[qdrant worker] all retries exhausted for job -> {task.job.value} session -> {task.uid}, err -> {e}"
                            )
            except asyncio.CancelledError:
                break
            finally:
                if task is not None:
                    self.jobs.task_done()

    async def finish_queue(self):
        await self.jobs.join()
