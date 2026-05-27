from fastapi import APIRouter, WebSocket


audo = APIRouter()


@audo.post("/audio/transcribe")
def transcribe_audio():
    pass

@audo.websocket()
