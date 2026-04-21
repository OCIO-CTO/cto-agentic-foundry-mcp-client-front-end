"""
Tests for speech_service.py module
"""
import pytest
from unittest.mock import patch, MagicMock
import azure.cognitiveservices.speech as speechsdk
import httpx


class TestGetSpeechConfig:
    """Tests for get_speech_config function"""

    def test_get_speech_config_success(self, mock_env_vars, mock_speech_config):
        """Test successful speech config creation"""
        from speech_service import get_speech_config

        config = get_speech_config()

        mock_speech_config.assert_called_once_with(
            subscription="test_key_12345",
            region="usgovvirginia"
        )

    def test_get_speech_config_missing_credentials(self, monkeypatch):
        """Test speech config creation fails with missing credentials"""
        monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
        monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

        # Reimport to pick up env changes
        import importlib
        import speech_service
        importlib.reload(speech_service)

        from speech_service import get_speech_config

        with pytest.raises(ValueError, match="credentials not configured"):
            get_speech_config()


class TestSynthesizeSpeech:
    """Tests for synthesize_speech function"""

    def test_synthesize_speech_success(self, mock_env_vars, mock_speech_config, mock_speech_synthesizer):
        """Test successful speech synthesis"""
        from speech_service import synthesize_speech

        audio_data = synthesize_speech("Hello world")

        assert audio_data == b'mock_audio_data'
        mock_speech_synthesizer.speak_text_async.assert_called_once_with("Hello world")

    def test_synthesize_speech_with_custom_voice(self, mock_env_vars, mock_speech_config, mock_speech_synthesizer):
        """Test speech synthesis with custom voice"""
        from speech_service import synthesize_speech

        audio_data = synthesize_speech("Hello world", voice_name="en-US-JennyNeural")

        assert audio_data == b'mock_audio_data'
        config_instance = mock_speech_config.return_value
        assert config_instance.speech_synthesis_voice_name == "en-US-JennyNeural"

    def test_synthesize_speech_canceled(self, mock_env_vars, mock_speech_config):
        """Test speech synthesis with canceled result"""
        with patch('azure.cognitiveservices.speech.SpeechSynthesizer') as mock_synth:
            synthesizer_instance = MagicMock()
            mock_synth.return_value = synthesizer_instance

            # Mock canceled result
            result = MagicMock()
            result.reason = speechsdk.ResultReason.Canceled
            cancellation_details = MagicMock()
            cancellation_details.reason = speechsdk.CancellationReason.Error
            cancellation_details.error_details = "Test error"
            result.cancellation_details = cancellation_details

            async_result = MagicMock()
            async_result.get.return_value = result
            synthesizer_instance.speak_text_async.return_value = async_result

            from speech_service import synthesize_speech

            with pytest.raises(ValueError, match="Speech synthesis failed"):
                synthesize_speech("Hello world")

    def test_synthesize_speech_missing_credentials(self, monkeypatch):
        """Test speech synthesis fails with missing credentials"""
        monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
        monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

        # Reimport to pick up env changes
        import importlib
        import speech_service
        importlib.reload(speech_service)

        from speech_service import synthesize_speech

        with pytest.raises(ValueError, match="credentials not configured"):
            synthesize_speech("Hello world")


class TestGetSpeechToken:
    """Tests for get_speech_token function"""

    def test_get_speech_token_success(self, mock_env_vars, mock_httpx_client):
        """Test successful token generation"""
        from speech_service import get_speech_token

        token_data = get_speech_token()

        assert token_data["token"] == "mock_token_12345"
        assert token_data["region"] == "usgovvirginia"

        mock_httpx_client.post.assert_called_once()
        call_args = mock_httpx_client.post.call_args
        assert "usgovvirginia.api.cognitive.microsoft.us" in call_args[0][0]
        assert call_args[1]["headers"]["Ocp-Apim-Subscription-Key"] == "test_key_12345"

    def test_get_speech_token_http_error(self, mock_env_vars):
        """Test token generation with HTTP error"""
        with patch('httpx.Client') as mock_client:
            client_instance = MagicMock()
            mock_client.return_value.__enter__.return_value = client_instance

            # Mock HTTP error
            client_instance.post.side_effect = httpx.HTTPError("Connection failed")

            from speech_service import get_speech_token

            with pytest.raises(ValueError, match="Failed to fetch speech token"):
                get_speech_token()

    def test_get_speech_token_missing_credentials(self, monkeypatch):
        """Test token generation fails with missing credentials"""
        monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
        monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

        # Reimport to pick up env changes
        import importlib
        import speech_service
        importlib.reload(speech_service)

        from speech_service import get_speech_token

        with pytest.raises(ValueError, match="credentials not configured"):
            get_speech_token()
