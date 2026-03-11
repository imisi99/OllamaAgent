from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from core.agent import get_graph, get_llm
from schemas.agent import SessionConversation, SessionState
from db.mongo import get_mongo_database

serve = APIRouter()


@serve.post("/agent/chat")
async def chat_agent(input: SessionConversation):
    db = get_mongo_database()
    if input["session_id"] == "":
        db.create_session({"messages": [], "created_at": datetime.now(), "name": ""})

    session = SessionState(
        {
            "llm": get_llm(),
            "message": input["message"],
            "session_id": input["session_id"],
            "response": "",
        }
    )
    response = await get_graph().ainvoke(session)

    return JSONResponse(status_code=200, content={"msg": response["response"]})


@serve.post("session/create")
async def create_session(input: SessionConversation):
    db = get_mongo_database()

    prompt = (
        "Generate a casual title for a chat session not more than 5 words using the user first input. You respond should be the title ONLY (one title) \n\n\n"
        + input["message"]["content"]
    )

    response = get_llm().invoke(prompt)
    title = "The LLM did a bad job"

    if isinstance(response.content, str):
        title = response.content

    created, id = db.create_session(
        {"messages": [], "created_at": datetime.now(), "name": title}
    )

    if not created:
        raise HTTPException(
            status_code=500, detail={"msg": "Failed to create the session."}
        )

    return JSONResponse(status_code=200, content={"id": id, "msg": "Success."})
