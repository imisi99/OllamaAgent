import logging
from datetime import datetime
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
from schemas.session import CreateSession

session = APIRouter()


@session.post("/session/create")
async def create_session(
    prompt: CreateSession,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
    model: Model = Depends(get_model),
):
    try:
        title = model.generate_title(prompt.prompt)
        uid = str(uuid4())

        sess: Session = {
            "_id": "",
            "uuid": uid,
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "name": title,
        }
        created, id = db.create_session(sess)

        if not created:
            raise Exception("MongoDB operation to create session was not acknowledged")

        qdb.add_job(Task(job=Job.CREATE_POINT, session=sess))

        return JSONResponse(
            status_code=status.HTTP_201_CREATED, content={"id": id, "uid": uid}
        )

    except Exception as e:
        logging.error(f"Failed to create session, An error occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to create the session."},
        )


@session.put("/session/rename/{session_id}/{session_uid}")
async def rename(
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
        logging.error(f"Failed to rename session, An errro occured -> {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to rename the session."},
        )


@session.put("/session/msg/{session_id}/{session_uid}")
async def add_message(
    message: Message,
    session_id: str,
    session_uid: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    try:
        created = db.add_messages(session_id, message)
        if not created:
            raise Exception("MongoDB operation to add message was not acknowledged")

        qdb.add_job(Task(job=Job.UPDATE_POINT, uid=session_uid, message=message))

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED, content={"msg": "Message added."}
        )

    except Exception as e:
        logging.error(
            f"Failed to add message for session -> {session_id}, An error occured -> {e}"
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Failed to add message to session."},
        )


@session.get("/session/all/preview")
async def fetch_all_session_preview(db: Database = Depends(get_mongo_database)):
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
            content={"msg": "Failed to fetch sessions."},
        )


@session.get("/session/all")
async def fetch_all_session(db: Database = Depends(get_mongo_database)):
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
async def fetch_single_session(
    session_id: str, db: Database = Depends(get_mongo_database)
):
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
            content={"msg": "Failed to fetch session."},
        )


@session.delete("/session/delete/{session_id}/{session_uid}")
async def delete_session(
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
            content={"msg": "Failed to delete the session."},
        )
