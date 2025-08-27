#!/usr/bin/env python3
"""Model download script for TTS Batch API container builds.

This script reads the model configuration and downloads the required
PIPER TTS models during container build time.
"""

import pathlib
import sys

import piper.download_voices as piper_download

# Add app directory to Python path for imports
app_dir = pathlib.Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from config import ModelConfig  # type: ignore[import-not-found]
except ImportError:
    # Fallback for container environment
    sys.path.insert(0, "/app")
    from app.config import ModelConfig  # type: ignore[import-not-found]


def main():
    """Download all configured models to the assets directory."""
    config = ModelConfig()

    print(f"Downloading models to: {config.assets_dir}")
    print(f"Available models: {config.available_models}")
    print(f"Default model: {config.get_effective_default_model()}")

    # Ensure assets directory exists
    config.assets_dir.mkdir(parents=True, exist_ok=True)

    # Download each configured model
    for model_name in config.available_models:
        print(f"Downloading model: {model_name}")
        try:
            piper_download.download_voice(model_name, config.assets_dir)
            print(f"✓ Downloaded: {model_name}")
        except Exception as e:
            print(f"✗ Failed to download {model_name}: {e}")
            # Don't exit on individual failures to allow partial downloads

    print("Model download completed.")


if __name__ == "__main__":
    main()
