import asyncio
import logging
from enum import Enum
from typing import Union, cast
from uuid import uuid4
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
)
from qdrant_client.http.models import UpdateStatus

from core.conf import CustomError
from core.emb import EmbeddingModel
from schemas.mongo import Message, Session
from schemas.qdrant import QSession


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

    async def create_point(self, session: Session) -> CustomError | None:
        vector: list[float] = [0] * 1024
        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=session["uuid"],
                    vector={"messages": vector},
                    payload={
                        "_id": session["_id"],
                        "uuid": session["uuid"],
                        "project_id": session["project_id"],
                        "name": session["name"],
                        "messages": [],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to create session with id -> {session['uuid']} result -> {result}"
            )

        return (
            None
            if success
            else CustomError(message="Failed to create session", code=500)
        )

    async def get_related_points(
        self,
        id: str,
        query: str = "",
        score_threshold: float = 0.5,
        use_query: bool = False,
        limit: int = 5,
    ) -> tuple[CustomError | None, tuple[list[tuple[QSession, float]], float] | None]:
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
                return CustomError(message="Point doesn't exist.", code=404), None

            vector = point[0].vector
            if vector is None:
                logging.error(
                    f"Tried to find related points with id -> {id} but point doesn't have a vector component"
                )
                return CustomError(message="Payload doesn't exist.", code=404), None

            if isinstance(vector, dict):
                vector = vector.get("messages")
                if vector is None:
                    logging.error(
                        f"Tried to find related points with id -> {id} but point doesn't have a message vector component"
                    )
                    return (
                        CustomError(
                            message="Message vector component doesn't exist.", code=404
                        ),
                        None,
                    )

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
            return None, None

        response: list[tuple[QSession, float]] = []
        avgScore = 0
        for point in result.points:
            if point.payload:
                payload = cast(QSession, point.payload)
                response.append((payload, point.score))
                avgScore += point.score

        avgScore /= len(response) if len(response) > 0 else 1
        logging.info(f"Recommended {len(response)} with an average score of {avgScore}")
        return None, (response, avgScore)

    async def update_point(self, uid: str, message: Message) -> CustomError | None:
        point = self.client.retrieve("chats", ids=[uid], with_payload=True)
        if not point:
            logging.error(
                f"Tried to update point with id -> {uid} but point doesn't exist in vector space."
            )
            return CustomError(message="Point doesn't exist.", code=404)

        payload = point[0].payload
        if not payload:
            logging.error(
                f"Tried to update point with id -> {uid} but payload doesn't exist"
            )
            return CustomError(message="Payload doesn't exist.", code=404)

        session = cast(QSession, payload)
        session["messages"].append(
            {"content": message["content"], "role": message["role"]}
        )

        vector = await self.embedding.generate_vector_embedding(session)

        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=uid,
                    vector={"messages": vector},
                    payload={
                        "_id": session["_id"],
                        "uuid": session["uuid"],
                        "name": session["name"],
                        "messages": session["messages"],
                        "project_id": session["project_id"],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to update session with id -> {id} result -> {result}, status -> {result.status}"
            )

        return (
            None
            if success
            else CustomError(message="Failed to update session", code=500)
        )

    async def update_payload(self, id: str, name: str) -> CustomError | None:
        point = self.client.retrieve(
            collection_name="chats", ids=[id], with_payload=False
        )

        if not point:
            logging.error(
                f"Tried to update payload with point id -> {id} but point doesn't exist in vector space."
            )
            return CustomError(message="Point doesn't exist.", code=404)

        result = self.client.set_payload(
            collection_name="chats", payload={"name": name}, points=[id]
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to update the title of point with id -> {id} result -> {result}"
            )

        return (
            None
            if success
            else CustomError(message="Failed to update session payload.", code=500)
        )

    async def delete_point(self, id: str) -> CustomError | None:
        point = self.client.retrieve(
            collection_name="chats", ids=[id], with_payload=False
        )

        if not point:
            logging.error(
                f"Tried to delete point with id -> {id} but point doesn't exist in vector space."
            )
            return CustomError(message="Point doesn't exist.", code=404)

        result = self.client.delete(collection_name="chats", points_selector=[id])

        result = self.client.delete(
            collection_name="chats",
            points_selector=FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="session_id", match=MatchValue(value=id))]
                )
            ),
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(f"Failed to delete point with id -> {id} result -> {result}")

        return (
            None
            if success
            else CustomError(message="Failed to delete session.", code=500)
        )

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
