from fastapi import APIRouter, Depends, WebSocket
from core.audio import Audio, get_audio_model


audo = APIRouter()


@audo.post("/audio/transcribe")
def transcribe_audio():
    pass


@audo.websocket("/ws")
async def real_time(websocket: WebSocket, audio: Audio = Depends(get_audio_model)):
    await websocket.accept()
    transcript_history: list[str] = []

    while True:
        chunk = await websocket.receive_bytes()
        transcipt = await audio.real_time_transcribe(chunk)
        if transcipt:
            transcript_history.append(transcipt)

            full_transcript = " ".join(transcript_history)
            await websocket.send_text(full_transcript)
