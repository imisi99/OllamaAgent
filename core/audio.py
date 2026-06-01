import io
import wave
from typing import Optional
from faster_whisper import WhisperModel
from schemas.mongo import Audio

# This current approach will work only with single connection multiple ws will break the buffer


class AudioModel:
    def __init__(self, model_path) -> None:
        self.model = WhisperModel(model_path, local_files_only=True, device="cuda")
        self.buffer = bytearray()
        self.BUFFER_THRESHOLD = 32000 * 2

    def preprocess(self, audio: Audio) -> io.BytesIO:
        return io.BytesIO(audio["audio"])

    def wrap_wav(self, pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(pcm)
        return buf.getvalue()

    def transcribe(self, audio: Audio) -> str:
        segments, _ = self.model.transcribe(self.preprocess(audio))
        return " ".join(seg.text for seg in segments)

    async def real_time_transcribe(self, chunk: bytes) -> str | None:
        self.buffer.extend(chunk)

        if len(self.buffer) < self.BUFFER_THRESHOLD:
            return None

        audio_bytes = bytes(self.buffer)
        self.buffer.clear()

        audio_io = io.BytesIO(self.wrap_wav(audio_bytes))
        segments, _ = self.model.transcribe(audio_io, language="en")
        return " ".join(seg.text for seg in segments)


AUDIO_MODEL: Optional[AudioModel] = None


def get_audio_model() -> AudioModel:
    if AUDIO_MODEL is None:
        raise Exception("The audio model is not initialized.")
    return AUDIO_MODEL


def create_audio_model(model_path: str) -> AudioModel:
    return AudioModel(model_path)
