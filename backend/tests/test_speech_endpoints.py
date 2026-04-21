"""
Tests for speech API endpoints in main.py
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    with patch('main.azure_client'):
        with patch('main.mcp'):
            from main import app
            return TestClient(app)


@pytest.fixture
def mock_synthesize_speech():
    """Mock the synthesize_speech function"""
    with patch('main.synthesize_speech') as mock:
        mock.return_value = b'test_audio_data'
        yield mock


@pytest.fixture
def mock_get_speech_token():
    """Mock the get_speech_token function"""
    with patch('main.get_speech_token') as mock:
        mock.return_value = {
            "token": "test_token_123",
            "region": "usgovvirginia"
        }
        yield mock


class TestSynthesizeEndpoint:
    """Tests for POST /api/speech/synthesize endpoint"""

    def test_synthesize_success(self, test_client, mock_synthesize_speech):
        """Test successful text-to-speech synthesis"""
        response = test_client.post(
            "/api/speech/synthesize",
            json={"text": "Hello world"}
        )

        assert response.status_code == 200
        assert response.content == b'test_audio_data'
        assert response.headers["content-type"] == "audio/mpeg"
        mock_synthesize_speech.assert_called_once_with("Hello world", None)

    def test_synthesize_with_voice(self, test_client, mock_synthesize_speech):
        """Test synthesis with custom voice"""
        response = test_client.post(
            "/api/speech/synthesize",
            json={"text": "Hello world", "voice": "en-US-JennyNeural"}
        )

        assert response.status_code == 200
        mock_synthesize_speech.assert_called_once_with("Hello world", "en-US-JennyNeural")

    def test_synthesize_missing_text(self, test_client):
        """Test synthesis without text parameter"""
        response = test_client.post(
            "/api/speech/synthesize",
            json={}
        )

        assert response.status_code == 400
        assert "Text is required" in response.json()["detail"]

    def test_synthesize_text_too_long(self, test_client):
        """Test synthesis with text exceeding limit"""
        long_text = "a" * 10001
        response = test_client.post(
            "/api/speech/synthesize",
            json={"text": long_text}
        )

        assert response.status_code == 400
        assert "Text too long" in response.json()["detail"]

    def test_synthesize_value_error(self, test_client, mock_synthesize_speech):
        """Test synthesis with service error"""
        mock_synthesize_speech.side_effect = ValueError("Service error")

        response = test_client.post(
            "/api/speech/synthesize",
            json={"text": "Hello world"}
        )

        assert response.status_code == 500
        assert "Service error" in response.json()["detail"]

    def test_synthesize_unexpected_error(self, test_client, mock_synthesize_speech):
        """Test synthesis with unexpected error"""
        mock_synthesize_speech.side_effect = Exception("Unexpected error")

        response = test_client.post(
            "/api/speech/synthesize",
            json={"text": "Hello world"}
        )

        assert response.status_code == 500
        assert "Speech synthesis failed" in response.json()["detail"]


class TestGetTokenEndpoint:
    """Tests for GET /api/speech/token endpoint"""

    def test_get_token_success(self, test_client, mock_get_speech_token):
        """Test successful token generation"""
        response = test_client.get("/api/speech/token")

        assert response.status_code == 200
        data = response.json()
        assert data["token"] == "test_token_123"
        assert data["region"] == "usgovvirginia"
        mock_get_speech_token.assert_called_once()

    def test_get_token_value_error(self, test_client, mock_get_speech_token):
        """Test token generation with service error"""
        mock_get_speech_token.side_effect = ValueError("Token service error")

        response = test_client.get("/api/speech/token")

        assert response.status_code == 500
        assert "Token service error" in response.json()["detail"]

    def test_get_token_unexpected_error(self, test_client, mock_get_speech_token):
        """Test token generation with unexpected error"""
        mock_get_speech_token.side_effect = Exception("Unexpected error")

        response = test_client.get("/api/speech/token")

        assert response.status_code == 500
        assert "Token generation failed" in response.json()["detail"]


class TestRateLimiting:
    """Tests for rate limiting on speech endpoints"""

    def test_rate_limit_not_exceeded(self, test_client, mock_synthesize_speech):
        """Test that a few requests succeed"""
        for _ in range(3):
            response = test_client.post(
                "/api/speech/synthesize",
                json={"text": "Test"}
            )
            assert response.status_code == 200
