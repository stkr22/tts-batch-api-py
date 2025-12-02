"""Request and response schemas for TTS Batch API.

This module defines Pydantic models for API request validation
and response formatting.
"""

from pydantic import BaseModel, field_validator


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


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
