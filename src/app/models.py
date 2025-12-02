"""Voice model management for TTS Batch API.

This module handles loading and management of PIPER TTS voice models
with support for multiple models and sample rate detection.
"""

import logging

import piper

from app import initialize_voice_engine as init_voice
from app.config import ModelConfig

logger = logging.getLogger("model_manager")


class ModelManager:
    """Manager for PIPER TTS voice models.

    Handles loading and storing multiple voice models using configurable
    settings. Caches all model metadata to avoid repeated disk I/O.
    """

    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()  # type: ignore[call-arg]

        # Cache config values to avoid repeated calls
        self.default_model_name = self.config.get_effective_default_model()
        self.available_models = {model_name: f"{model_name}.onnx" for model_name in self.config.available_models}

        # Model storage
        self.models: dict[str, piper.PiperVoice] = {}

        # AIDEV-NOTE: performance-cache; sample rates read once during load to avoid disk I/O
        self.model_sample_rates: dict[str, int] = {}

    def load_models(self) -> None:
        """Load all configured voice models and cache their sample rates."""
        logger.info("Loading models: %s", list(self.available_models.keys()))
        logger.info("Default model: %s", self.default_model_name)

        # Load all configured models and cache their sample rates
        for model_name, model_file in self.available_models.items():
            try:
                # Load the model
                self.models[model_name] = init_voice.initialize_voice_engine(model_file)

                # Read and cache the sample rate once
                sample_rate = self.config.get_model_sample_rate(model_name)
                self.model_sample_rates[model_name] = sample_rate

                logger.info("Loaded model: %s (%s) - %d Hz", model_name, model_file, sample_rate)
            except Exception as e:
                logger.warning("Failed to load model %s: %s", model_name, e)

    def get_model(self, model_name: str | None = None) -> piper.PiperVoice:
        """Get a loaded model by name, or default if None.

        Args:
            model_name: Name of the model to retrieve, or None for default

        Returns:
            The loaded PiperVoice model

        Raises:
            KeyError: If model is not loaded
        """
        effective_name = self.get_effective_model_name(model_name)

        if effective_name not in self.models:
            available = list(self.models.keys())
            raise KeyError(f"Model '{effective_name}' not available. Available models: {available}")

        return self.models[effective_name]

    def get_model_sample_rate(self, model_name: str | None = None) -> int:
        """Get the native sample rate for a voice model.

        Returns cached sample rate - no disk I/O after initial load.

        Args:
            model_name: Model identifier, or None for default model

        Returns:
            Native sample rate in Hz (cached from model configuration)

        Raises:
            KeyError: If model sample rate is not cached
        """
        effective_name = self.get_effective_model_name(model_name)

        if effective_name not in self.model_sample_rates:
            available = list(self.model_sample_rates.keys())
            raise KeyError(f"Sample rate for '{effective_name}' not cached. Available: {available}")

        return self.model_sample_rates[effective_name]

    def get_effective_model_name(self, model_name: str | None = None) -> str:
        """Get the effective model name, resolving None to default.

        Args:
            model_name: Requested model name, or None for default

        Returns:
            Actual model name to use (cached, no config calls)
        """
        return model_name or self.default_model_name

    def get_available_models(self) -> list[str]:
        """Get list of available model names.

        Returns:
            List of loaded model names
        """
        return list(self.models.keys())

    def clear_models(self) -> None:
        """Clear all loaded models and cached data."""
        self.models.clear()
        self.model_sample_rates.clear()
