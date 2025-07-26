import os
import pathlib

import piper
import piper.download_voices as piper_download

from .logger import logger


def get_writable_directory() -> pathlib.Path:
    """Determine a writable directory for storing model data."""
    assets_dir = pathlib.Path(os.getenv("ASSETS_DIR", "/app/assets"))
    if os.access(assets_dir, os.W_OK):
        logger.info("Using writable application directory: %s", assets_dir)
        return assets_dir
    home_directory = pathlib.Path.home()
    logger.warning(
        "Application directory %s is not writable; defaulting to home directory: %s", assets_dir, home_directory
    )
    return home_directory


def initialize_voice_engine(model: str) -> piper.PiperVoice:
    """Initialize the voice engine, downloading the model if necessary."""
    assets_dir = pathlib.Path(os.getenv("ASSETS_DIR", "/app/assets"))
    model_path = assets_dir / model
    model_config_path = assets_dir / f"{model}.json"

    if not model_path.exists() or not model_config_path.exists():
        download_dir = get_writable_directory()
        logger.info("Model %s not found locally. Attempting to download.", model)

        # Extract voice name from model file (remove .onnx extension)
        voice_name = model.replace(".onnx", "")
        
        # Download the voice using the new API
        piper_download.download_voice(voice_name, download_dir)
        logger.info("Model %s downloaded successfully.", voice_name)
        
        # Update paths to the downloaded model
        model_path = download_dir / model
        model_config_path = download_dir / f"{model}.json"
    else:
        logger.info("Model %s found locally at %s.", model, model_path)

    logger.info("Loading Piper voice model from %s with config.", model)
    return piper.PiperVoice.load(model_path)
