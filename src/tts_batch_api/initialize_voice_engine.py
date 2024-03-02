import pathlib
from typing import Any

import piper  # ignore
from piper import download as piper_download


def initialize_voice_engine(model: str) -> piper.PiperVoice:
    download_dir = pathlib.Path.cwd()
    data_dir = [download_dir]
    model_path = pathlib.Path(model)
    if not model_path.exists():
        # Load voice info
        voices_info = piper_download.get_voices(download_dir, update_voices=False)

        # Resolve aliases for backwards compatibility with old voice names
        aliases_info: dict[str, Any] = {}
        for voice_info in voices_info.values():
            for voice_alias in voice_info.get("aliases", []):
                aliases_info[voice_alias] = {"_is_alias": True, **voice_info}

        voices_info.update(aliases_info)
        piper_download.ensure_voice_exists(model, data_dir, download_dir, voices_info)
        model, config = piper_download.find_voice(model, data_dir)

    return piper.PiperVoice.load(model, config_path=config)
