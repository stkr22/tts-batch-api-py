"""FastAPI application for TTS Batch API.

Main application file that orchestrates the TTS service with caching,
model management, and audio processing capabilities.
"""

import os
import time
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Header, HTTPException, responses
from piper import SynthesisConfig

from app.audio_processing import resample_audio
from app.cache import CacheConfig, TTSCache
from app.config import ModelConfig
from app.logger import logger
from app.models import ModelManager
from app.schemas import HealthResponse, SynthesizeRequest

# AIDEV-NOTE: global-state; application-level model and cache instances
model_config = ModelConfig()  # type: ignore[call-arg]
model_manager = ModelManager(model_config)
cache: TTSCache | None = None


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

    # Load voice models using configuration
    model_manager.load_models()

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
    model_manager.clear_models()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint for container orchestration.

    Returns basic health status without authentication requirements.
    Used by Kubernetes probes and load balancers.

    Returns:
        Dict with health status indicator

    """
    return HealthResponse(status="healthy")


# AIDEV-NOTE: main-endpoint; core TTS synthesis with sample rate conversion and A/B testing
@app.post("/synthesizeSpeech")
async def synthesize_speech(  # noqa: PLR0915, PLR0912
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

    # Get model and its sample rate (None uses default from config)
    model_name = synthesize_request.model
    try:
        voice_engine = model_manager.get_model(model_name)
        native_sample_rate = model_manager.get_model_sample_rate(model_name)
        effective_model_name = model_manager.get_effective_model_name(model_name)
    except (KeyError, ValueError) as e:
        if isinstance(e, KeyError):
            available = model_manager.get_available_models()
            detail = f"Model '{model_name}' not available. Available models: {available}"
        else:
            detail = str(e)
        raise HTTPException(status_code=400, detail=detail) from e

    target_sample_rate = synthesize_request.sample_rate

    # Cache at target sample rate for efficiency
    cache_key = f"{effective_model_name}:{target_sample_rate}:{synthesize_request.text}"

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
                    effective_model_name,
                    target_sample_rate,
                    cache_time * 1000,
                )
                return responses.Response(
                    content=cached_audio,
                    media_type="audio/x-raw",
                    headers={
                        "Content-Length": str(len(cached_audio)),
                        "X-Model": effective_model_name,
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
        effective_model_name,
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
            "X-Model": effective_model_name,
            "X-Sample-Rate": str(target_sample_rate),
            "X-Cache": cache_status,
            "X-Resampling": "APPLIED" if resampling_applied else "NONE",
            "X-Synthesis-Time": f"{synthesis_time * 1000:.1f}ms",
            "X-Resample-Time": f"{resample_time * 1000:.1f}ms",
            "X-Total-Time": f"{total_time * 1000:.1f}ms",
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8181)
