import hashlib
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

import piper
from fastapi import FastAPI, Header, HTTPException, responses
from piper import SynthesisConfig
from pydantic import BaseModel
from redis import asyncio as aioredis

from . import initialize_voice_engine as init_voice


@dataclass
class CacheConfig:
    enabled: bool = True
    ttl: int = 60 * 60 * 24 * 7  # 7 days in seconds


class TTSCache:
    def __init__(self, redis_url: str, config: CacheConfig) -> None:
        self.redis = aioredis.from_url(redis_url)
        self.config = config
        self.logger = logging.getLogger("tts_cache")

    def _generate_cache_key(self, text: str, voice_id: str = "default") -> str:
        """Generate a deterministic cache key for the TTS request."""
        key_content = f"{voice_id}:{text}"
        return f"tts:{hashlib.sha256(key_content.encode()).hexdigest()}"

    async def get(self, text: str, voice_id: str = "default") -> bytes | None:
        """Retrieve cached audio data if available."""
        if not self.config.enabled:
            self.logger.info("Cache disabled, skipping lookup")
            return None

        cache_key = self._generate_cache_key(text, voice_id)
        cached_data: bytes = await self.redis.get(cache_key)  # type: ignore

        if cached_data:
            self.logger.info("Cache HIT for text: %s (key: %s)", text[:50], cache_key)
        else:
            self.logger.info("Cache MISS for text: %s (key: %s)", text[:50], cache_key)

        return cached_data

    async def set(self, text: str, audio_data: bytes, voice_id: str = "default") -> None:
        """Store audio data in cache."""
        if not self.config.enabled:
            self.logger.info("Cache disabled, skipping storage")
            return

        cache_key = self._generate_cache_key(text, voice_id)
        await self.redis.setex(cache_key, self.config.ttl, audio_data)
        self.logger.info(
            "Cached %d bytes for text: %s (key: %s, TTL: %d)", len(audio_data), text[:50], cache_key, self.config.ttl
        )

    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis.close()


class SynthesizeRequest(BaseModel):
    text: str


ml_models: dict[str, piper.PiperVoice] = {}
cache: TTSCache | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    global cache  # noqa: PLW0603

    ml_models["voice_engine"] = init_voice.initialize_voice_engine(
        os.getenv("TTS_MODEL", "en_US-kathleen-low.onnx"),
    )
    redis_pw = os.getenv("REDIS_PASSWORD")
    redis_url = "redis://"
    if redis_pw:
        redis_url = f"{redis_url}:{redis_pw}@"
    redis_url = f"{redis_url}{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}"
    cache = TTSCache(
        redis_url=redis_url,
        config=CacheConfig(
            enabled=os.getenv("ENABLE_CACHE", "true").lower() == "true",
            ttl=int(os.getenv("CACHE_TTL", "604800")),
        ),
    )

    yield

    if cache:
        await cache.close()
    ml_models.clear()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/synthesizeSpeech")
async def synthesize_speech(
    synthesize_request: SynthesizeRequest,
    user_token: Annotated[str | None, Header()] = None,
) -> responses.Response:
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)

    if not cache:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    # Try to get from cache first
    cached_audio = await cache.get(synthesize_request.text)
    if cached_audio:
        return responses.Response(
            content=cached_audio,
            media_type="audio/x-raw",
            headers={"Content-Length": str(len(cached_audio))},
        )

    # If not in cache, generate new audio
    voice_engine = ml_models["voice_engine"]

    # Use the new synthesis API with default config
    synthesis_config = SynthesisConfig()
    audio_chunks = voice_engine.synthesize(synthesize_request.text, synthesis_config)

    # Convert audio chunks to bytes for caching
    audio_data = b"".join(chunk.audio_int16_bytes for chunk in audio_chunks)

    # Store in cache asynchronously
    await cache.set(synthesize_request.text, audio_data)

    return responses.Response(
        content=audio_data,
        media_type="audio/x-raw",
        headers={"Content-Length": str(len(audio_data))},
    )
