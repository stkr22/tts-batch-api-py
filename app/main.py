import hashlib
import logging
import math
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

import numpy as np
import piper
from fastapi import FastAPI, Header, HTTPException, responses
from piper import SynthesisConfig
from pydantic import BaseModel, field_validator
from redis import asyncio as aioredis
from scipy import signal

from . import initialize_voice_engine as init_voice
from .logger import logger


# AIDEV-NOTE: audio-resampling; high-quality sample rate conversion for device compatibility
def resample_audio(audio_data: bytes, original_rate: int, target_rate: int) -> bytes:
    """Resample audio data with high-quality anti-aliasing.

    Uses scipy.signal.resample_poly for professional-grade audio resampling
    with automatic anti-aliasing filter to prevent frequency folding artifacts.

    Args:
        audio_data: Raw 16-bit PCM audio bytes
        original_rate: Source sample rate in Hz
        target_rate: Target sample rate in Hz

    Returns:
        Resampled audio as 16-bit PCM bytes

    Raises:
        ValueError: If sample rates are invalid or zero
    """
    if original_rate == target_rate:
        return audio_data

    if original_rate <= 0 or target_rate <= 0:
        raise ValueError(f"Invalid sample rates: {original_rate} -> {target_rate}")

    # Convert bytes to numpy array (16-bit signed integers)
    audio_array = np.frombuffer(audio_data, dtype=np.int16)

    # Calculate resampling ratio using greatest common divisor for efficiency
    gcd = math.gcd(target_rate, original_rate)
    up_factor = target_rate // gcd
    down_factor = original_rate // gcd

    # Perform high-quality resampling with anti-aliasing
    # resample_poly automatically applies appropriate anti-aliasing filter
    resampled_array = signal.resample_poly(audio_array, up_factor, down_factor)

    # Convert back to 16-bit integers and return as bytes
    return resampled_array.astype(np.int16).tobytes()  # type: ignore[no-any-return]


# AIDEV-NOTE: model-utilities; helper functions for model metadata and sample rates
def get_model_sample_rate(model_name: str) -> int:
    """Get the native sample rate for a voice model.

    Returns the sample rate from model configuration to determine
    if resampling is needed for the target sample rate.

    Args:
        model_name: Model identifier (kathleen-low, ryan-medium, etc.)

    Returns:
        Native sample rate in Hz

    Raises:
        ValueError: If model is unknown
    """
    model_sample_rates = {
        "kathleen-low": 16000,
        "ryan-medium": 22050,
        "default": 22050,  # Default to ryan-medium rate
    }

    if model_name not in model_sample_rates:
        raise ValueError(f"Unknown model: {model_name}")

    return model_sample_rates[model_name]


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

    async def aclose(self) -> None:
        """Close Redis connection gracefully.

        Called during application shutdown to clean up resources.
        """
        await self.redis.aclose()


class SynthesizeRequest(BaseModel):
    """Request model for text-to-speech synthesis.

    Attributes:
        text: Input text to convert to speech (max ~500 chars recommended)
        sample_rate: Target sample rate in Hz (16000, 22050, 44100, 48000)
        model: Voice model to use (optional, defaults to ryan-medium)
    """

    text: str
    sample_rate: int = 16000
    model: str | None = None  # Optional model override for testing

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: int) -> int:
        """Validate that sample rate is supported."""
        supported_rates = [16000, 22050, 44100, 48000]
        if v not in supported_rates:
            raise ValueError(f"Sample rate {v} not supported. Use one of: {supported_rates}")
        return v


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

    # Initialize available voice models for A/B testing
    available_models = {
        "kathleen-low": "en_US-kathleen-low.onnx",
        "ryan-medium": "en_US-ryan-medium.onnx",
    }

    # Load default model (optimized for quality - ryan-medium proven superior)
    default_model = os.getenv("TTS_MODEL", "en_US-ryan-medium.onnx")
    ml_models["default"] = init_voice.initialize_voice_engine(default_model)

    # Load all available models for A/B testing
    for model_name, model_file in available_models.items():
        try:
            ml_models[model_name] = init_voice.initialize_voice_engine(model_file)
            logger.info("Loaded model: %s (%s)", model_name, model_file)
        except Exception as e:
            logger.warning("Failed to load model %s: %s", model_name, e)

    # Initialize cache if Redis is available and enabled
    cache_enabled = os.getenv("ENABLE_CACHE", "true").lower() == "true"

    if cache_enabled:
        try:
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
                    enabled=True,
                    ttl=int(os.getenv("CACHE_TTL", "604800")),
                ),
            )
            logger.info("Cache initialized successfully")
        except Exception as e:
            logger.warning("Failed to initialize cache: %s. Running without cache.", e)
            cache = None
    else:
        logger.info("Cache disabled via ENABLE_CACHE=false")
        cache = None

    yield  # Application runs here

    # Cleanup resources on shutdown
    if cache:
        try:
            await cache.aclose()
        except Exception as e:
            logger.warning("Cache cleanup failed: %s", e)
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


# AIDEV-NOTE: main-endpoint; core TTS synthesis with sample rate conversion and A/B testing
@app.post("/synthesizeSpeech")
async def synthesize_speech(  # noqa: PLR0915
    synthesize_request: SynthesizeRequest,
    user_token: Annotated[str | None, Header()] = None,
) -> responses.Response:
    """Convert text to speech with intelligent caching and sample rate conversion.

    Supports multiple voice models and automatic resampling to match target
    device requirements. Audio is cached at the requested sample rate for
    optimal performance.

    Args:
        synthesize_request: Request with text, sample_rate, and optional model
        user_token: Authentication token from header

    Returns:
        Response with audio/x-raw content at requested sample rate

    Raises:
        HTTPException: 403 for auth failure, 400 for invalid model, 500 for system errors
    """
    start_time = time.time()

    # Authentication check
    if user_token != os.environ["ALLOWED_USER_TOKEN"]:
        raise HTTPException(status_code=403)

    # Determine which model to use
    model_name = synthesize_request.model or "default"
    if model_name not in ml_models:
        available = list(ml_models.keys())
        raise HTTPException(
            status_code=400, detail=f"Model '{model_name}' not available. Available models: {available}"
        )

    # Get model's native sample rate
    try:
        native_sample_rate = get_model_sample_rate(model_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    target_sample_rate = synthesize_request.sample_rate

    # Cache at target sample rate for efficiency
    cache_key = f"{model_name}:{target_sample_rate}:{synthesize_request.text}"

    # Cache-first pattern: check for audio at target sample rate (if cache available)
    cached_audio = None
    cache_status = "DISABLED"

    if cache:
        try:
            cached_audio = await cache.get(cache_key)
            if cached_audio:
                cache_time = time.time() - start_time
                cache_status = "HIT"
                logger.info(
                    "Cache HIT: %s, model=%s, target=%d, time=%.2fms",
                    synthesize_request.text[:50],
                    model_name,
                    target_sample_rate,
                    cache_time * 1000,
                )
                return responses.Response(
                    content=cached_audio,
                    media_type="audio/x-raw",
                    headers={
                        "Content-Length": str(len(cached_audio)),
                        "X-Model": model_name,
                        "X-Sample-Rate": str(target_sample_rate),
                        "X-Cache": cache_status,
                        "X-Resampling": "NONE",
                    },
                )
            cache_status = "MISS"
        except Exception as e:
            logger.warning("Cache lookup failed: %s", e)
            cache_status = "ERROR"
    else:
        logger.info("Cache disabled, synthesizing fresh audio")

    # Cache miss: synthesize audio with selected model
    synthesis_start = time.time()
    voice_engine = ml_models[model_name]
    synthesis_config = SynthesisConfig()

    try:
        audio_chunks = voice_engine.synthesize(synthesize_request.text, synthesis_config)
        audio_data = b"".join(chunk.audio_int16_bytes for chunk in audio_chunks)
    except Exception as e:
        logger.error("TTS synthesis failed: %s", e)
        raise HTTPException(status_code=500, detail="Audio synthesis failed") from e

    synthesis_time = time.time() - synthesis_start

    # Apply resampling if needed
    resample_start = time.time()
    resampling_applied = False

    if native_sample_rate != target_sample_rate:
        try:
            audio_data = resample_audio(audio_data, native_sample_rate, target_sample_rate)
            resampling_applied = True
        except Exception as e:
            logger.error("Audio resampling failed: %s", e)
            raise HTTPException(status_code=500, detail="Audio resampling failed") from e

    resample_time = time.time() - resample_start

    # Store in cache for future requests (if cache available)
    if cache:
        try:
            await cache.set(cache_key, audio_data)
        except Exception as e:
            logger.warning("Cache storage failed: %s", e)

    total_time = time.time() - start_time

    # Performance logging
    logger.info(
        "Synthesis: %s, model=%s, native=%d, target=%d, synthesis=%.2fms, resample=%.2fms, total=%.2fms",
        synthesize_request.text[:50],
        model_name,
        native_sample_rate,
        target_sample_rate,
        synthesis_time * 1000,
        resample_time * 1000,
        total_time * 1000,
    )

    return responses.Response(
        content=audio_data,
        media_type="audio/x-raw",
        headers={
            "Content-Length": str(len(audio_data)),
            "X-Model": model_name,
            "X-Sample-Rate": str(target_sample_rate),
            "X-Cache": cache_status,
            "X-Resampling": "APPLIED" if resampling_applied else "NONE",
            "X-Synthesis-Time": f"{synthesis_time * 1000:.1f}ms",
            "X-Resample-Time": f"{resample_time * 1000:.1f}ms",
            "X-Total-Time": f"{total_time * 1000:.1f}ms",
        },
    )
