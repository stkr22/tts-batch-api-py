import base64
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated

import numpy as np
import piper  # ignore
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from tts_batch_api import initialize_voice_engine as init_voice

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

ml_models: dict[str, piper.PiperVoice] = {}


class AudioData(BaseModel):
    audio_base64: str
    dtype: str = "float32"


class SynthesizeRequest(BaseModel):
    text: str
    samplerate: int = 16000  # this only has the effect that blocksize is adjusted / silence is added. No resampling is done.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    ml_models["voice_engine"] = init_voice.initialize_voice_engine(
        os.getenv("TTS_MODEL", "en_US-kathleen-low"),
    )
    yield
    # Clean up the ML models and release the resources
    ml_models.clear()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.post("/synthesizeSpeech")
async def synthesize_speech(
    synthesize_request: SynthesizeRequest,
    user_token: Annotated[str | None, Header()] = None,
) -> AudioData:
    voice_engine = ml_models["voice_engine"]
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)
    audio_frames = None
    for audio_byte in voice_engine.synthesize_stream_raw(synthesize_request.text):
        n_array = np.frombuffer(audio_byte, dtype=np.int16)
        if audio_frames is None:
            audio_frames = n_array
        else:
            audio_frames = np.concatenate((audio_frames, n_array), axis=0)
    if audio_frames is None:
        raise HTTPException(
            status_code=400, detail="Generation Error, no bytes generated."
        )
    if (remainder := audio_frames.shape[0] % synthesize_request.samplerate) != 0:
        lengths = [(0, 0)] * audio_frames.ndim
        padding_needed = synthesize_request.samplerate - remainder
        lengths[0] = (0, padding_needed)
        audio_frames = np.pad(audio_frames, lengths, "constant")
    audio_np = audio_frames.tobytes()
    base64_bytes = base64.b64encode(audio_np)
    base64_string = base64_bytes.decode("utf-8")

    return AudioData(audio_base64=base64_string, dtype="int16")
