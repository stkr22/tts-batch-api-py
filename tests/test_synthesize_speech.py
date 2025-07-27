import os

import pytest
from fastapi.testclient import TestClient

from app import main

# Constants
HTTP_OK = 200


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
            json={"sample_rate": 16000, "text": "Hello!"},
        )
        if response.status_code != HTTP_OK:
            print(f"Response content: {response.text}")
        assert response.status_code == HTTP_OK, f"HTTP Code should be 200, got {response.status_code}: {response.text}"
