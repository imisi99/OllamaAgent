import asyncio
import json
from datetime import datetime
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from core.agent import Model, get_model
from core.mongo import Database
from core.qdrant import Job, Qdrant, Task
from db.mongo import get_mongo_database
from db.qdrant import get_qdrant_database
from schemas.agent import SessionConversation, SessionState
from schemas.mongo import Message

serve = APIRouter()

# TODO: The Flow from the chatting to the summarizing of message for the embed cuts of the chatting ? (This happens at somewhat every run ?) This also happens twice ?
# This stuff doesn't add to the redis when it does the summarizer which is what i'm guessing is causing this stuff to happen like this


@serve.post("/agent/chat")
async def chat_agent(input: SessionConversation, model: Model = Depends(get_model)):
    session = SessionState(
        {
            "ghost_session": input["ghost_session"],
            "user_id": input["user_id"],
            "message": input["message"],
            "session_id": input["session_id"],
            "session_uid": input["session_uid"],
            "response": "",
            "chunks": [],
        }
    )
    response = await model.chat(session)

    return JSONResponse(status_code=200, content={"msg": response["response"]})


@serve.post("/agent/chat/stream")
async def stream_chat(
    input: SessionConversation,
    model: Model = Depends(get_model),
    db: Database = Depends(get_mongo_database),
    qdb: Qdrant = Depends(get_qdrant_database),
):
    session = SessionState(
        {
            "ghost_session": input["ghost_session"],
            "user_id": input["user_id"],
            "message": input["message"],
            "session_id": input["session_id"],
            "session_uid": input["session_uid"],
            "response": "",
            "chunks": [],
        }
    )

    queue: asyncio.Queue = asyncio.Queue()

    async def run_and_save():
        full_response = ""
        thought_response = ""
        try:
            async for token in model.stream_chat(session):
                await queue.put(token)
                if token["type"] == "text":
                    full_response += token["content"]
                elif token["type"] == "reason":
                    thought_response += token["content"]

        except Exception as e:
            logging.error(f"[AGENT] Streaming error -> {e}")
        finally:
            await queue.put(None)
            if not input["ghost_session"] and full_response:
                message: Message = {
                    "content": full_response,
                    "thought": thought_response,
                    "session_id": input["session_id"],
                    "role": "assistant",
                    "audio": None,
                    "timestamp": datetime.now(),
                    "images": [],
                    "files": [],
                }

                err = db.create_message(message)

                if err:
                    logging.error(
                        "[AGENT][MONGO] Failed to update chat response to mongo"
                    )
                    return JSONResponse(status_code=err.code, content=err.message)

                qdb.add_job(
                    Task(Job.UPDATE_POINT, uid=input["session_uid"], message=message)
                )

    asyncio.create_task(run_and_save())

    async def token_generator():
        while True:
            token = await queue.get()
            if token is None:
                break
            yield json.dumps(token)

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )
