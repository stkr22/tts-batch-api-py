import os

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def set_env_vars():
    os.environ["ALLOWED_USER_TOKEN"] = "DEBUG"
    os.environ["ASSETS_DIR"] = "./assets"
    os.environ["ENABLE_CACHE"] = "false"
    yield
    # Optionally reset or delete the variables after tests
    os.environ.pop("ALLOWED_USER_TOKEN", None)


def test_synthesize_speech():
    with TestClient(main.app) as client:
        response = client.post(
            "/synthesizeSpeech",
            headers={"user-token": "DEBUG"},
            json={"samplerate": 16000, "text": "Hello!"},
        )
        assert response.status_code == 200, "HTTP Code should be 200"
