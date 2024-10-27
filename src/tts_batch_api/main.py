import os
from contextlib import asynccontextmanager
from typing import Annotated

import piper
from fastapi import FastAPI, Header, HTTPException, responses
from pydantic import BaseModel

from tts_batch_api import initialize_voice_engine as init_voice

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
) -> responses.StreamingResponse:
    voice_engine = ml_models["voice_engine"]
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)

    return responses.StreamingResponse(
        voice_engine.synthesize_stream_raw(synthesize_request.text),
        media_type="audio/wav",
    )
