import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated

import piper  # ignore
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
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


class SynthesizeRequest(BaseModel):
    text: str


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
) -> StreamingResponse:
    voice_engine = ml_models["voice_engine"]
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)

    async def audio_streamer():
        try:
            for audio_byte in voice_engine.synthesize_stream_raw(
                synthesize_request.text
            ):
                yield audio_byte  # Directly yield the bytes received
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during streaming: {e}")

    return StreamingResponse(audio_streamer(), media_type="audio/wav")
