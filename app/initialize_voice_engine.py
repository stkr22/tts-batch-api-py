import os
import pathlib
from typing import Any

import piper
from piper import download as piper_download

from app.logger import logger


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

    if not model_path.exists() and not model_config_path.exists():
        download_dir = get_writable_directory()
        data_dir = [download_dir]
        logger.info("Model %s not found locally. Attempting to download.", model)

        # Load voice information
        voices_info = piper_download.get_voices(download_dir, update_voices=False)
        logger.info("Available voices info retrieved. Total voices available: %d", len(voices_info))

        # Resolve aliases for backwards compatibility
        aliases_info: dict[str, Any] = {}
        for voice_name, voice_info in voices_info.items():
            for voice_alias in voice_info.get("aliases", []):
                aliases_info[voice_alias] = {"_is_alias": True, **voice_info}
                logger.debug("Alias '%s' resolved for voice '%s'.", voice_alias, voice_name)

        voices_info.update(aliases_info)
        logger.info("Aliases resolved. Checking if model %s exists in voices info.", model)

        # Download and verify the specified model
        piper_download.ensure_voice_exists(model, data_dir, download_dir, voices_info)
        model_path, model_config_path = piper_download.find_voice(model, data_dir)
        logger.info("Model %s downloaded and located successfully.", model)
    else:
        logger.info("Model %s found locally at %s.", model, model_path)

    logger.info("Loading Piper voice model from %s with config.", model)
    return piper.PiperVoice.load(model_path, config_path=model_config_path)
