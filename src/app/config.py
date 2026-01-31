"""Configuration management for TTS Batch API.

This module provides centralized configuration using pydantic-settings
for model management, download strategy, and runtime settings.
"""

import json
import pathlib
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ModelConfig(BaseSettings):
    """Configuration for TTS model management.

    Handles model selection, download configuration, and runtime settings
    using environment variables with sensible defaults.
    """

    model_config = {"arbitrary_types_allowed": True, "env_prefix": "TTS_", "case_sensitive": False}

    # Model configuration
    available_models: Annotated[
        list[str],
        Field(
            default=["en_US-kathleen-low", "en_US-ryan-medium"],
            description="List of available PIPER TTS models to download and use",
        ),
    ]

    default_model: Annotated[
        str,
        Field(default="en_US-kathleen-low", description="Default model to use when no model is specified in requests"),
    ]

    # Directory configuration
    assets_dir: Annotated[
        pathlib.Path, Field(default=pathlib.Path("/app/assets"), description="Directory where model files are stored")
    ]

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, v: str, info) -> str:
        """Ensure default model is in available models list."""
        available = info.data.get("available_models", [])
        if v not in available:
            # Convert from ONNX filename to model name if needed
            model_name = v.replace(".onnx", "") if v.endswith(".onnx") else v
            if model_name not in available:
                raise ValueError(f"Default model '{v}' not in available models: {available}")
            return model_name
        return v

    def get_effective_default_model(self) -> str:
        """Get the effective default model."""
        return self.default_model

    def get_model_file_path(self, model_name: str) -> pathlib.Path:
        """Get the full path to a model's ONNX file."""
        return self.assets_dir / f"{model_name}.onnx"

    def get_model_config_path(self, model_name: str) -> pathlib.Path:
        """Get the full path to a model's JSON configuration file."""
        return self.assets_dir / f"{model_name}.onnx.json"

    def get_model_sample_rate(self, model_name: str) -> int:
        """Extract sample rate from model's JSON configuration file.

        Args:
            model_name: Model identifier (e.g., 'en_US-kathleen-low')

        Returns:
            Native sample rate in Hz from model configuration

        Raises:
            FileNotFoundError: If model config file doesn't exist
            ValueError: If sample rate cannot be extracted from config

        """
        config_path = self.get_model_config_path(model_name)

        if not config_path.exists():
            raise FileNotFoundError(f"Model config not found: {config_path}")

        try:
            with config_path.open() as f:
                config_data = json.load(f)

            # Extract sample rate from PIPER model configuration
            # The sample rate is typically in config_data["audio"]["sample_rate"]
            audio_config = config_data.get("audio", {})
            sample_rate = audio_config.get("sample_rate")

            if sample_rate is None:
                raise ValueError(f"No sample_rate found in {config_path}")

            return int(sample_rate)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Failed to extract sample rate from {config_path}: {e}") from e
