"""Caching functionality for TTS Batch API.

This module provides Redis-based caching for synthesized audio data
with configurable TTL and efficient key generation.
"""

import hashlib
import logging
from dataclasses import dataclass

from redis import asyncio as aioredis


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
        """Initialize the TTS cache.

        Args:
            redis_url: Redis connection URL with optional authentication
            config: Cache configuration including TTL and enable/disable flag

        """
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
        cached_data: bytes = await self.redis.get(cache_key)  # type: ignore[assignment]

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
