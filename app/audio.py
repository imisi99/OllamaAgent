from fastapi import APIRouter, Depends, WebSocket
from fastapi.responses import JSONResponse
from starlette import status
from core.audio import AudioModel, get_audio_model
from schemas.mongo import Audio


audio = APIRouter()


@audio.post("/audio/transcribe")
def transcribe_audio(input: Audio, audio: AudioModel = Depends(get_audio_model)):
    try:
        transcipt = audio.transcribe(input["audio"])
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": f"Failed to transcribe audio -> {e}"},
        )
    return JSONResponse(
        status_code=status.HTTP_200_OK, content={"transcipt": transcipt}
    )


@audio.websocket("/ws")
async def real_time(websocket: WebSocket, audio: AudioModel = Depends(get_audio_model)):
    await websocket.accept()
    transcript_history: list[str] = []

    while True:
        chunk = await websocket.receive_bytes()
        transcipt = await audio.real_time_transcribe(chunk)
        if transcipt:
            transcript_history.append(transcipt)

            full_transcript = " ".join(transcript_history)
            await websocket.send_text(full_transcript)
