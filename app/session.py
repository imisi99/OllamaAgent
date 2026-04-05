import logging
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from core.agent import generate_title
from core.mongo import Database
from core.qdrant import Job, Qdrant, Task
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from schemas.agent import SessionConversation
from schemas.mongo import Message, Session

session = APIRouter()

# TODO: Check if it's possible to use actual datetime for the created at in both the session and message
# See if it's possible to get the actual errors for failed ops to log them


@session.post("/session/create")
async def create_session(
    input: SessionConversation,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    try:
        title = generate_title(input["message"]["content"])
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
            return JSONResponse(
                status_code=500, content={"msg": "Failed to create the session."}
            )

        qdb.add_job(Task(job=Job.CREATE_POINT, session=sess))

    except Exception as e:
        logging.error(f"Failed to create session, An error occured -> {e}")
        return JSONResponse(
            status_code=500, content={"msg": "Failed to create the session"}
        )

    return JSONResponse(status_code=200, content={"id": id, "uid": uid})


@session.post("/session/msg/{session_id}")
async def add_message(
    message: Message,
    session_id: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    created = db.add_messages(session_id, message)
    if not created:
        return JSONResponse(
            status_code=500, content={"msg": "Failed to add message to session."}
        )
    qdb.add_job(Task(job=Job.UPDATE_POINT, uid="", message=message))
    return JSONResponse(status_code=200, content={"msg": "Message added."})


@session.get("/session/all")
async def fetch_all_session(db: Database = Depends(get_mongo_database)):
    sessions = db.fetch_all_session()
    if sessions is None or len(sessions) == 0:
        return JSONResponse(status_code=404, content={"msg": "No session created yet."})
    return JSONResponse(status_code=200, content={"sessions": sessions})


@session.get("/session/all/preview")
async def fetch_all_session_preview(db: Database = Depends(get_mongo_database)):
    sessions = db.fetch_all_session_preview()
    if sessions is None or len(sessions) == 0:
        return JSONResponse(status_code=404, content={"msg": "No session created yet."})
    return JSONResponse(status_code=200, content={"sessions": sessions})


@session.get("/session/{session_id}")
async def fetch_single_session(
    session_id: str, db: Database = Depends(get_mongo_database)
):
    s_session = db.fetch_session(session_id)
    if s_session is None:
        return JSONResponse(
            status_code=404,
            content={"msg": f"Session with id -> {session_id} not found."},
        )
    return JSONResponse(status_code=200, content={"session": s_session})


@session.delete("/session/delete/{session_id}")
async def delete_session(
    session_id: str,
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    deleted = db.delete_session(session_id)
    if not deleted:
        return JSONResponse(
            status_code=500, content={"msg": "Failed to delete the session."}
        )

    qdb.delete_point(session_id)

    return JSONResponse(status_code=200, content={"msg": "Session deleted."})
