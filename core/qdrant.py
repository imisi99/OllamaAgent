import logging
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from qdrant_client.http.models import UpdateStatus
from schemas.mongo import Session


class Qdrant:
    def __init__(self, client: QdrantClient, embedding: str) -> None:
        self.client = client
        self.embedding = embedding

    def create_point(self, id: str, session: Session) -> bool:
        vector = [0.1]
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

    def update_point(self, id: str, session: Session) -> bool:
        point = self.client.retrieve("chats", ids=[id])
        if not point:
            logging.error(
                f"Tried to update point with id -> {id} but point doesn't exist in vector space."
            )
            return False

        vector = [0.1]
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
            logging.error(
                f"Failed to update session with id -> {id} result -> {result}"
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
            vector = [
                0.1
            ]  # TODO: Transform the query to a vector using the embedding param
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
