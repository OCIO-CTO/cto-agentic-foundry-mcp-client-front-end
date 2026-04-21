"""
Pytest configuration and fixtures for backend tests
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import azure.cognitiveservices.speech as speechsdk


@pytest.fixture
def mock_speech_config():
    """Mock Azure Speech SDK configuration"""
    with patch('azure.cognitiveservices.speech.SpeechConfig') as mock:
        config_instance = MagicMock()
        mock.return_value = config_instance
        yield mock


@pytest.fixture
def mock_speech_synthesizer():
    """Mock Azure Speech Synthesizer"""
    with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock:
        synthesizer_instance = MagicMock()
        mock.return_value = synthesizer_instance

        # Mock successful synthesis result
        result = MagicMock()
        result.reason = speechsdk.ResultReason.SynthesizingAudioCompleted
        result.audio_data = b'mock_audio_data'

        # Mock async result
        async_result = MagicMock()
        async_result.get.return_value = result
        synthesizer_instance.speak_text_async.return_value = async_result

        yield synthesizer_instance


@pytest.fixture
def mock_speech_recognizer():
    """Mock Azure Speech Recognizer"""
    with patch('azure.cognitiveservices.speech.SpeechRecognizer') as mock:
        recognizer_instance = MagicMock()
        mock.return_value = recognizer_instance
        yield recognizer_instance


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for token fetching"""
    with patch('httpx.Client') as mock_client:
        client_instance = MagicMock()
        mock_client.return_value.__enter__.return_value = client_instance

        # Mock successful token response
        response = MagicMock()
        response.text = 'mock_token_12345'
        response.raise_for_status = MagicMock()
        client_instance.post.return_value = response

        yield client_instance


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up environment variables for testing"""
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test_key_12345")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "usgovvirginia")
    yield
