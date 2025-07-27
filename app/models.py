"""Voice model management for TTS Batch API.

This module handles loading and management of PIPER TTS voice models
with support for multiple models and sample rate detection.
"""

import logging

import piper

from . import initialize_voice_engine as init_voice

logger = logging.getLogger("model_manager")


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


class ModelManager:
    """Manager for PIPER TTS voice models.
    
    Handles loading and storing multiple voice models for A/B testing
    and production use. Provides model metadata and validation.
    """
    
    def __init__(self) -> None:
        self.models: dict[str, piper.PiperVoice] = {}
        self.available_models = {
            "kathleen-low": "en_US-kathleen-low.onnx",
            "ryan-medium": "en_US-ryan-medium.onnx",
        }
    
    def load_models(self, default_model_file: str) -> None:
        """Load all available voice models.
        
        Args:
            default_model_file: Default model file to load (for backward compatibility)
        """
        # Load default model (optimized for quality - ryan-medium proven superior)
        self.models["default"] = init_voice.initialize_voice_engine(default_model_file)
        
        # Load all available models for A/B testing
        for model_name, model_file in self.available_models.items():
            try:
                self.models[model_name] = init_voice.initialize_voice_engine(model_file)
                logger.info("Loaded model: %s (%s)", model_name, model_file)
            except Exception as e:
                logger.warning("Failed to load model %s: %s", model_name, e)
    
    def get_model(self, model_name: str) -> piper.PiperVoice:
        """Get a loaded model by name.
        
        Args:
            model_name: Name of the model to retrieve
            
        Returns:
            The loaded PiperVoice model
            
        Raises:
            KeyError: If model is not loaded
        """
        if model_name not in self.models:
            available = list(self.models.keys())
            raise KeyError(f"Model '{model_name}' not available. Available models: {available}")
        
        return self.models[model_name]
    
    def get_available_models(self) -> list[str]:
        """Get list of available model names.
        
        Returns:
            List of loaded model names
        """
        return list(self.models.keys())
    
    def clear_models(self) -> None:
        """Clear all loaded models."""
        self.models.clear()