import asyncio
import logging
from typing import cast
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.http.models import UpdateStatus
from emb import EmbeddingModel
from schemas.mongo import Message, Session


class Qdrant:
    def __init__(self, client: QdrantClient, embedding: EmbeddingModel) -> None:
        self.client = client
        self.embedding = embedding
        self.jobs: asyncio.Queue[tuple[str, Message]] = asyncio.Queue()

    def create_point(self, id: str, session: Session) -> bool:
        vector = self.embedding.generate_vector_embedding(session)
        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=id,
                    vector={"description": vector},
                    payload={
                        "id": session["_id"],
                        "title": session["name"],
                        "message": session["messages"],
                        "created_at": session["created_at"],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            logging.error(
                f"Failed to create session with id -> {id} result -> {result}"
            )
        return success

    def get_related_points(
        self,
        id: str,
        query: str,
        score_threshold: float,
        use_query: bool = False,
        limit: int = 5,
    ) -> tuple[list[tuple[Session, float]], float] | None:
        vector = None
        if use_query:
            vector = self.embedding.generate_vector_embedding_query(query)
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
        )

        response: list[tuple[Session, float]] = []
        avgScore = 0
        for point in result.points:
            payload = point.payload
            if payload is not None:
                session: Session = {
                    "_id": payload["id"],
                    "created_at": payload["created_at"],
                    "name": payload["name"],
                    "messages": payload["messages"],
                }
                response.append((session, point.score))
                avgScore += point.score

        avgScore /= len(response) if len(response) > 0 else 1
        logging.info(f"Recommended {len(response)} with an average score of {avgScore}")
        return response, avgScore

    def delete_point(self, id: str) -> bool:
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

    def _update_point(self, id: str, message: Message):
        point = self.client.retrieve("chats", ids=[id], with_payload=True)
        if not point:
            logging.error(
                f"Tried to update point with id -> {id} but point doesn't exist in vector space."
            )
            return

        payload = point[0].payload
        if not payload:
            logging.error(
                f"Tried to update point with id -> {id} but payload doesn't exist"
            )
            return

        payload["messages"].append(message)
        session = cast(Session, payload)

        vector = self.embedding.generate_vector_embedding(session)
        result = self.client.upsert(
            collection_name="chats",
            points=[
                PointStruct(
                    id=id,
                    vector={"messages": vector},
                    payload={
                        "id": session["_id"],
                        "title": session["name"],
                        "message": session["messages"],
                        "created_at": session["created_at"],
                    },
                )
            ],
        )

        success = result.status in (UpdateStatus.COMPLETED, UpdateStatus.ACKNOWLEDGED)
        if not success:
            raise RuntimeError(
                f"Failed to update session with id -> {id} result -> {result}, status -> {result.status}"
            )

    def add_job(self, session_id: str, message: Message):
        self.jobs.put_nowait((session_id, message))

    async def worker(self):
        MAX_ATTEMPTS = 3
        while True:
            try:
                session_id, message = await self.jobs.get()
                for attempts in range(MAX_ATTEMPTS):
                    try:
                        self._update_point(session_id, message)
                        break
                    except Exception as e:
                        if attempts < MAX_ATTEMPTS - 1:
                            logging.error(
                                f"[qdrant worker] attempt {attempts + 1} failed, retrying... error -> {e}"
                            )
                            await asyncio.sleep(1.5 * attempts)
                        else:
                            logging.error(
                                f"[qdrant worker] all retries exhausted for session -> {session_id}, err -> {e}"
                            )

            finally:
                self.jobs.task_done()

    async def finish_queue(self):
        await self.jobs.join()
