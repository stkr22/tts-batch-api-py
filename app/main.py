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


# AIDEV-NOTE: cache-config; centralized caching configuration for Redis TTL management
@dataclass
class CacheConfig:
    """Configuration for TTS audio caching system.

    Attributes:
        enabled: Whether caching is enabled (can be disabled for testing)
        ttl: Time-to-live in seconds for cached audio data (default: 7 days)
    """

    enabled: bool = True
    ttl: int = 60 * 60 * 24 * 7  # 7 days in seconds


# AIDEV-NOTE: performance-critical; Redis caching for audio synthesis results
class TTSCache:
    """High-performance Redis-based cache for synthesized audio data.

    This class implements a cache-first pattern for TTS synthesis results,
    significantly reducing computation time for repeated text requests.
    Cache keys are deterministic SHA256 hashes of voice_id:text combinations.

    Args:
        redis_url: Redis connection URL with optional authentication
        config: Cache configuration including TTL and enable/disable flag
    """

    def __init__(self, redis_url: str, config: CacheConfig) -> None:
        self.redis = aioredis.from_url(redis_url)
        self.config = config
        self.logger = logging.getLogger("tts_cache")

    def _generate_cache_key(self, text: str, voice_id: str = "default") -> str:
        """Generate a deterministic cache key for the TTS request.

        Uses SHA256 hash of voice_id:text to create collision-resistant keys.
        The 'tts:' prefix helps with Redis key organization and debugging.

        Args:
            text: Input text for synthesis
            voice_id: Voice model identifier (future multi-voice support)

        Returns:
            Hex-encoded SHA256 hash prefixed with 'tts:'
        """
        key_content = f"{voice_id}:{text}"
        return f"tts:{hashlib.sha256(key_content.encode()).hexdigest()}"

    async def get(self, text: str, voice_id: str = "default") -> bytes | None:
        """Retrieve cached audio data if available.

        Implements cache-first pattern with detailed logging for debugging.
        Returns None for both cache misses and disabled cache.

        Args:
            text: Input text to lookup
            voice_id: Voice model identifier

        Returns:
            Cached audio bytes or None if not found/disabled
        """
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
        """Store audio data in cache with TTL.

        Uses Redis SETEX for atomic set-with-expiration operation.
        Logs cache storage for monitoring and debugging.

        Args:
            text: Input text that was synthesized
            audio_data: Raw audio bytes to cache
            voice_id: Voice model identifier
        """
        if not self.config.enabled:
            self.logger.info("Cache disabled, skipping storage")
            return

        cache_key = self._generate_cache_key(text, voice_id)
        await self.redis.setex(cache_key, self.config.ttl, audio_data)
        self.logger.info(
            "Cached %d bytes for text: %s (key: %s, TTL: %d)", len(audio_data), text[:50], cache_key, self.config.ttl
        )

    async def close(self) -> None:
        """Close Redis connection gracefully.

        Called during application shutdown to clean up resources.
        """
        await self.redis.close()


class SynthesizeRequest(BaseModel):
    """Request model for text-to-speech synthesis.

    Attributes:
        text: Input text to convert to speech (max ~500 chars recommended)
    """

    text: str


# AIDEV-NOTE: global-state; application-level model and cache instances
ml_models: dict[str, piper.PiperVoice] = {}  # Global voice model storage
cache: TTSCache | None = None  # Global cache instance


# AIDEV-NOTE: startup-shutdown; FastAPI lifespan for resource management
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """FastAPI lifespan context manager for startup/shutdown tasks.

    Handles:
    - Voice model loading during startup
    - Redis connection initialization
    - Graceful resource cleanup on shutdown

    Args:
        app: FastAPI application instance (unused but required by protocol)
    """
    global cache  # noqa: PLW0603

    # Initialize voice engine with configured model
    ml_models["voice_engine"] = init_voice.initialize_voice_engine(
        os.getenv("TTS_MODEL", "en_US-kathleen-low.onnx"),
    )

    # Build Redis URL with optional authentication
    redis_pw = os.getenv("REDIS_PASSWORD")
    redis_url = "redis://"
    if redis_pw:
        redis_url = f"{redis_url}:{redis_pw}@"
    redis_url = f"{redis_url}{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}"

    # Initialize cache with environment-based configuration
    cache = TTSCache(
        redis_url=redis_url,
        config=CacheConfig(
            enabled=os.getenv("ENABLE_CACHE", "true").lower() == "true",
            ttl=int(os.getenv("CACHE_TTL", "604800")),
        ),
    )

    yield  # Application runs here

    # Cleanup resources on shutdown
    if cache:
        await cache.close()
    ml_models.clear()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for container orchestration.

    Returns basic health status without authentication requirements.
    Used by Kubernetes probes and load balancers.

    Returns:
        Dict with health status indicator
    """
    return {"status": "healthy"}


# AIDEV-NOTE: main-endpoint; core TTS synthesis with caching strategy
@app.post("/synthesizeSpeech")
async def synthesize_speech(
    synthesize_request: SynthesizeRequest,
    user_token: Annotated[str | None, Header()] = None,
) -> responses.Response:
    """Convert text to speech with intelligent caching.

    Implements cache-first pattern: checks Redis cache before synthesis.
    Returns raw 16-bit PCM audio data at 22050 Hz mono.

    Args:
        synthesize_request: Request containing text to synthesize
        user_token: Authentication token from header

    Returns:
        Response with audio/x-raw content and proper headers

    Raises:
        HTTPException: 403 for auth failure, 500 for system errors
    """
    # Authentication check
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)

    if not cache:
        raise HTTPException(status_code=500, detail="Cache not initialized")

    # Cache-first pattern: try to get from cache first
    cached_audio = await cache.get(synthesize_request.text)
    if cached_audio:
        return responses.Response(
            content=cached_audio,
            media_type="audio/x-raw",
            headers={"Content-Length": str(len(cached_audio))},
        )

    # Cache miss: generate new audio using PIPER TTS
    voice_engine = ml_models["voice_engine"]

    # Use default synthesis configuration
    synthesis_config = SynthesisConfig()
    audio_chunks = voice_engine.synthesize(synthesize_request.text, synthesis_config)

    # Convert audio chunks to bytes for caching and response
    audio_data = b"".join(chunk.audio_int16_bytes for chunk in audio_chunks)

    # Store in cache for future requests
    await cache.set(synthesize_request.text, audio_data)

    return responses.Response(
        content=audio_data,
        media_type="audio/x-raw",
        headers={"Content-Length": str(len(audio_data))},
    )
