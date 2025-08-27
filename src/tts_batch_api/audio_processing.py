"""Audio processing utilities for TTS Batch API.

This module provides high-quality audio resampling functionality
using scipy for professional-grade audio processing.
"""

import math

import numpy as np
from scipy import signal


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
