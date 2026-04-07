from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.agent import get_graph, get_llm_no_reasoning
from schemas.agent import SessionConversation, SessionState

serve = APIRouter()

# TODO: User gRPC for this instead ? (what are the gains)


@serve.post("/agent/chat")
def chat_agent(input: SessionConversation):
    session = SessionState(
        {
            "ghost_session": input["ghost_session"],
            "user_id": input["user_id"],
            "llm": get_llm_no_reasoning(),
            "message": input["message"],
            "session_id": input["session_id"],
            "response": "",
        }
    )
    response = get_graph().invoke(session)

    return JSONResponse(status_code=200, content={"msg": response["response"]})
