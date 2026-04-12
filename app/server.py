from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from core.agent import Model, get_model
from schemas.agent import SessionConversation, SessionState

serve = APIRouter()

# TODO: User gRPC for this instead ? (what are the gains)


@serve.post("/agent/chat")
def chat_agent(input: SessionConversation, model: Model = Depends(get_model)):
    session = SessionState(
        {
            "ghost_session": input["ghost_session"],
            "user_id": input["user_id"],
            "message": input["message"],
            "session_id": input["session_id"],
            "response": "",
        }
    )
    response = model.chat(session)

    return JSONResponse(status_code=200, content={"msg": response["response"]})
