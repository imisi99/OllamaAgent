import copy
import logging
import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from starlette import status

from core.agent import get_model, Model
from core.mongo import Database
from core.qdrant import Job, Qdrant, Task
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from schemas.mongo import Message, Session
from schemas.session import CreateSession, SimilarSessions

session = APIRouter()


@session.post("/session/create")
def create_session(
    prompt: CreateSession,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
    model: Model = Depends(get_model),
):
    try:
        title = "Untitled"

        if not prompt.prompt and not prompt.audio:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"msg": "No content to create chat with."},
            )

        if prompt.audio and not prompt.audio["transcript"] and not prompt.prompt:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"msg": "No prompt and the audio is silent."},
            )

        title = model.generate_title(prompt.prompt, prompt.audio)

        uid = str(uuid4())

        sess: Session = {
            "_id": "",
            "uuid": uid,
            "messages": [
                {
                    "timestamp": datetime.datetime.now(),
                    "thought": "",
                    "audio": prompt.audio,
                    "content": prompt.prompt,
                    "files": prompt.files,
                    "images": prompt.images,
                    "role": "user",
                }
            ],
            "created_at": datetime.datetime.now(),
            "name": title,
        }

        created, id = db.create_session(copy.deepcopy(sess))

        if not created:
            raise Exception("MongoDB operation to create session was not acknowledged")

        sess["_id"] = id

        qdb.add_job(Task(job=Job.CREATE_POINT, session=sess))

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"id": id, "uid": uid, "title": title},
        )

    except Exception as e:
        logging.error(f"Failed to create session, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to create the session -> {e}."},
        )

@session.create("/session/projects/create")
def create_project(name: str, db: Database = Depends(get_mongo_database)):
    try:
        created = db.create_project()
        if not created:
            raise Exception("DB operation to create project failed.")
    except Exception as e:
        logging.error(f"Failed to create project, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to create the project -> {e}."},
        )

@session.put("/session/projects/{session_id}/{project_id}")
def add_to_project(
    project_id: str,
    session_id: str,
    db: Database = Depends(get_mongo_database)
):
    try:
        pass
    except Exception as e:
        pass

@session.delete("/session/project/remove/{session_id}/{project_id}")
def remove_from_project(
    session_id: str,
    project_id: str,
    db: Database = Depends(get_mongo_database)
):
    try:
        pass
    except Exception as e:
        pass
    

@session.put("/session/rename/{session_id}/{session_uid}")
def rename(
    session_id: str,
    session_uid: str,
    name: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    try:
        updated = db.rename_session(session_id, name)
        if not updated:
            raise Exception("MongoDB operation to rename session not acknowledged.")

        qdb.add_job(Task(uid=session_uid, job=Job.UPDATE_PAYLOAD, name=name))

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Session renamed successfully."},
        )

    except Exception as e:
        logging.error(f"Failed to rename session, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to rename the session -> {e}."},
        )


@session.put("/session/msg/{session_id}/{session_uid}")
def add_message(
    message: Message,
    session_id: str,
    session_uid: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    try:
        if not message["content"] and not message["audio"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"msg": "No content to create chat with."},
            )

        if (
            message["audio"]
            and not message["audio"]["transcript"]
            and not message["content"]
        ):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"msg": "No prompt and the audio is silent."},
            )

        message["timestamp"] = datetime.datetime.now()

        created = db.add_messages(session_id, copy.deepcopy(message))
        if not created:
            raise Exception("MongoDB operation to add message was not acknowledged")

        qdb.add_job(Task(job=Job.UPDATE_POINT, uid=session_uid, message=message))

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"msg": "Message added."},
        )

    except Exception as e:
        logging.error(
            f"Failed to add message for session -> {session_id}, An error occured -> {e}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to add message to session -> {e}."},
        )


@session.get("/session/all/preview")
def fetch_all_session_preview(db: Database = Depends(get_mongo_database)):
    try:
        sessions = db.fetch_all_session_preview()
        if sessions is None or len(sessions) == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"msg": "No session created yet."},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"sessions": sessions}
        )

    except Exception as e:
        logging.error(f"Failed to retrieve sessions for preview -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to fetch sessions -> {e}."},
        )


@session.get("/session/all")
def fetch_all_session(db: Database = Depends(get_mongo_database)):
    try:
        sessions = db.fetch_all_session()
        if sessions is None or len(sessions) == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"msg": "No session created yet."},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"sessions": sessions}
        )

    except Exception as e:
        logging.error(f"Failed to retrieve sessions -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to fetch sessions."},
        )


@session.get("/session/{session_id}")
def fetch_single_session(session_id: str, db: Database = Depends(get_mongo_database)):
    try:
        s_session = db.fetch_session(session_id)
        if s_session is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"msg": f"Session with id -> {session_id} not found."},
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"session": s_session}
        )

    except Exception as e:
        logging.error(f"Failed to retrieve session -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to fetch session -> {e}."},
        )


@session.get("/session/find/similar")
async def fetch_similar_sessions(
    details: SimilarSessions, qdb: Qdrant = Depends(get_qdrant_database)
):
    try:
        result = await qdb.get_related_points(
            details.uid,
            score_threshold=details.threshold,
            limit=details.limit,
        )

        if result is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "msg": "No similar sessions available, maybe reduce threshold."
                },
            )

        points, avgScore = result

        points_score: list[tuple[Session, float]] = [
            (
                Session(
                    {
                        "name": sess["name"],
                        "_id": sess["_id"],
                        "created_at": sess["created_at"],
                        "messages": [],
                        "uuid": sess["uuid"],
                    }
                ),
                score,
            )
            for sess, score in points
        ]

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"score": avgScore, "sessions": points_score},
        )
    except Exception as e:
        logging.error(f"Failed to fetch similar sessions -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to fetch similar sessions -> {e}."},
        )


@session.delete("/session/delete/{session_id}/{session_uid}")
def delete_session(
    session_id: str,
    session_uid: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    try:
        deleted = db.delete_session(session_id)
        if not deleted:
            raise Exception("MongoDB operation to delete session was not acknowledged.")

        qdb.add_job(Task(uid=session_uid, job=Job.DELETE_POINT))

        return JSONResponse(
            status_code=status.HTTP_200_OK, content={"msg": "Session deleted."}
        )

    except Exception as e:
        logging.error(f"Failed to delete session with id -> {session_id}, error -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to delete session -> {e}."},
        )
