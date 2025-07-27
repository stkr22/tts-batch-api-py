import os
from unittest.mock import Mock, patch

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


@patch("app.main.model_manager")
def test_synthesize_speech(mock_model_manager):
    # Mock the model manager to avoid loading real models
    mock_voice_engine = Mock()
    mock_voice_engine.synthesize.return_value = [
        Mock(audio_int16_bytes=b"fake_audio_data_chunk")
    ]
    
    mock_model_manager.get_model.return_value = mock_voice_engine
    mock_model_manager.get_model_sample_rate.return_value = 16000
    mock_model_manager.get_effective_model_name.return_value = "test-model"
    mock_model_manager.get_available_models.return_value = ["test-model"]
    
    with TestClient(main.app) as client:
        response = client.post(
            "/synthesizeSpeech",
            headers={"user-token": "DEBUG"},
            json={"sample_rate": 16000, "text": "Hello!"},
        )
        if response.status_code != HTTP_OK:
            print(f"Response content: {response.text}")
        assert response.status_code == HTTP_OK, f"HTTP Code should be 200, got {response.status_code}: {response.text}"
        
        # Verify the response contains audio data
        assert len(response.content) > 0
        assert response.headers["content-type"] == "audio/x-raw"
        assert response.headers["x-model"] == "test-model"
        assert response.headers["x-sample-rate"] == "16000"