import logging
from datetime import datetime
from os import stat
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from core.agent import get_llm
from core.mongo import Database
from db.mongo import get_mongo_database
from schemas.agent import SessionConversation
from schemas.mongo import Message

session = APIRouter()

# TODO: Check if it's possible to use actual datetime for the created at in both the session and message
# See if it's possible to get the actual errors for failed ops to log them


@session.post("/session/create")
async def create_session(
    input: SessionConversation, db: Database = Depends(get_mongo_database)
):
    prompt = (
        "Generate a casual title for a chat session not more than 5 words using the user first input. You respond should be the title ONLY (one title) without the string quote an example is \n Explaining Docker Compose \n \n\n\n"
        + input["message"]["content"]
    )

    response = get_llm().invoke(prompt)
    title = "The LLM did a bad job"

    logging.info(response)

    if isinstance(response.content, str):
        title = response.content

    created, id = db.create_session(
        {
            "_id": "",
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "name": title,
        }
    )

    if not created:
        raise HTTPException(
            status_code=500, detail={"msg": "Failed to create the session."}
        )

    return JSONResponse(status_code=200, content={"id": id})


@session.post("/session/msg/{session_id}")
async def add_message(
    message: Message, session_id: str, db: Database = Depends(get_mongo_database)
):
    created = db.add_messages(session_id, message)
    if not created:
        raise HTTPException(
            status_code=500, detail={"msg": "Failed to add message to session."}
        )
    return JSONResponse(status_code=200, content={"msg": "Message added."})


@session.get("/session/all")
async def fetch_all_session(db: Database = Depends(get_mongo_database)):
    sessions = db.fetch_all_session()
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
async def delete_session(session_id: str, db: Database = Depends(get_mongo_database)):
    deleted = db.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=500, detail={"msg": "Failed to delete the session."}
        )

    return JSONResponse(status_code=200, content={"msg": "Session deleted."})
