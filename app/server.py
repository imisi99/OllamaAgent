import json
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from core.agent import Model, get_model
from schemas.agent import SessionConversation, SessionState

serve = APIRouter()

# TODO: Fix the on_stream_chat with the summarizer.


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
async def stream_chat(input: SessionConversation, model: Model = Depends(get_model)):
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

    async def token_generator():
        async for token in model.stream_chat(session):
            yield json.dumps(token)

    return StreamingResponse(
        token_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )
