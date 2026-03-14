import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.agent import get_graph, get_llm
from schemas.agent import SessionConversation, SessionState

serve = APIRouter()


@serve.post("/agent/chat")
async def chat_agent(input: SessionConversation):
    session = SessionState(
        {
            "llm": get_llm(),
            "message": input["message"],
            "session_id": input["session_id"],
            "response": "",
        }
    )
    response = await get_graph().ainvoke(session)
    logging.info(response)

    return JSONResponse(status_code=200, content={"msg": response["response"]})
