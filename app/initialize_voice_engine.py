import os
import pathlib

import piper
import piper.download_voices as piper_download

from .logger import logger


# AIDEV-NOTE: filesystem-fallback; handles read-only container environments
def get_writable_directory() -> pathlib.Path:
    """Determine a writable directory for storing model data.

    Tries assets directory first, falls back to home directory for
    read-only filesystems (common in container security constraints).

    Returns:
        Path to writable directory for model storage
    """
    assets_dir = pathlib.Path(os.getenv("ASSETS_DIR", "/app/assets"))
    if os.access(assets_dir, os.W_OK):
        logger.info("Using writable application directory: %s", assets_dir)
        return assets_dir
    home_directory = pathlib.Path.home()
    logger.warning(
        "Application directory %s is not writable; defaulting to home directory: %s", assets_dir, home_directory
    )
    return home_directory


# AIDEV-NOTE: model-management; auto-download and loading of PIPER voice models
def initialize_voice_engine(model: str) -> piper.PiperVoice:
    """Initialize the voice engine, downloading the model if necessary.

    Implements auto-download strategy: checks for local model files first,
    downloads from PIPER repository if missing. Handles both .onnx model
    and .json configuration files.

    Args:
        model: Model filename (e.g., 'en_US-kathleen-low.onnx')

    Returns:
        Loaded PiperVoice instance ready for synthesis

    Raises:
        Various exceptions from piper.PiperVoice.load() for invalid models
    """
    assets_dir = pathlib.Path(os.getenv("ASSETS_DIR", "/app/assets"))
    model_path = assets_dir / model
    model_config_path = assets_dir / f"{model}.json"

    # Check if model files exist locally
    if not model_path.exists() or not model_config_path.exists():
        download_dir = get_writable_directory()
        logger.info("Model %s not found locally. Attempting to download.", model)

        # Extract voice name from model file (remove .onnx extension)
        voice_name = model.replace(".onnx", "")

        # Download the voice using PIPER's download API
        piper_download.download_voice(voice_name, download_dir)
        logger.info("Model %s downloaded successfully.", voice_name)

        # Update paths to the downloaded model location
        model_path = download_dir / model
        model_config_path = download_dir / f"{model}.json"
    else:
        logger.info("Model %s found locally at %s.", model, model_path)

    # Load the PIPER voice model with configuration
    logger.info("Loading Piper voice model from %s with config.", model)
    return piper.PiperVoice.load(model_path)
