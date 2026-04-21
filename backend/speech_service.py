"""
Azure Speech Services Integration Module
Provides text-to-speech and speech-to-text functionality
"""
import logging
from typing import Optional, Dict
import azure.cognitiveservices.speech as speechsdk
from config import config
from exceptions import SpeechServiceError, log_error

logger = logging.getLogger(__name__)


def get_speech_config() -> speechsdk.SpeechConfig:
    """
    Create and return Azure Speech SDK configuration

    Returns:
        speechsdk.SpeechConfig: Configured speech config object

    Raises:
        SpeechServiceError: If credentials are not configured
    """
    if not config.AZURE_SPEECH_KEY or not config.AZURE_SPEECH_REGION:
        raise SpeechServiceError(
            "Azure Speech Services credentials not configured. "
            "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables."
        )

    speech_config = speechsdk.SpeechConfig(
        subscription=config.AZURE_SPEECH_KEY,
        region=config.AZURE_SPEECH_REGION
    )

    # Set audio format for synthesis
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    return speech_config


def synthesize_speech(text: str, voice_name: Optional[str] = None) -> bytes:
    """
    Convert text to speech audio bytes

    Args:
        text: Text to convert to speech
        voice_name: Optional voice name (e.g., 'en-US-JennyNeural')
                   Defaults to 'en-US-AriaNeural' if not specified

    Returns:
        bytes: Audio data in MP3 format

    Raises:
        SpeechServiceError: If credentials not configured or synthesis fails
    """
    try:
        speech_config = get_speech_config()

        # Set voice if specified
        voice_name = voice_name or "en-US-AriaNeural"
        speech_config.speech_synthesis_voice_name = voice_name

        # Create synthesizer with no audio output (we'll capture bytes)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None  # None means in-memory result
        )

        logger.info(f"Synthesizing speech for text (length: {len(text)}): {text[:50]}...")
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(f"Speech synthesis completed, audio size: {len(result.audio_data)} bytes")
            return result.audio_data

        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            error_msg = f"Speech synthesis canceled: {cancellation_details.reason}"

            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                error_msg = f"Speech synthesis failed: {cancellation_details.error_details}"
                logger.error(f"Error details: {cancellation_details.error_details}")

            raise SpeechServiceError(error_msg)
        else:
            raise SpeechServiceError(f"Unexpected synthesis result: {result.reason}")

    except SpeechServiceError:
        raise
    except Exception as e:
        log_error(e, "Error in speech synthesis")
        raise SpeechServiceError(f"Speech synthesis failed: {str(e)}")


def get_speech_token() -> Dict[str, str]:
    """
    Generate an authentication token for frontend Speech SDK usage
    Token is valid for 10 minutes

    Returns:
        dict: Contains 'token' and 'region' keys

    Raises:
        SpeechServiceError: If credentials not configured or token fetch fails
    """
    try:
        if not config.AZURE_SPEECH_KEY or not config.AZURE_SPEECH_REGION:
            raise SpeechServiceError("Azure Speech Services credentials not configured")

        import httpx

        token_url = f"https://{config.AZURE_SPEECH_REGION}.api.cognitive.microsoft.us/sts/v1.0/issueToken"
        headers = {
            "Ocp-Apim-Subscription-Key": config.AZURE_SPEECH_KEY
        }

        logger.info(f"Fetching speech token from: {token_url}")

        with httpx.Client(timeout=10.0) as client:
            response = client.post(token_url, headers=headers)
            response.raise_for_status()

            token = response.text
            logger.info("Successfully obtained speech token")

            return {
                "token": token,
                "region": config.AZURE_SPEECH_REGION
            }

    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch speech token: {str(e)}"
        log_error(e, "HTTP error fetching speech token")
        raise SpeechServiceError(error_msg)
    except SpeechServiceError:
        raise
    except Exception as e:
        log_error(e, "Error fetching speech token")
        raise SpeechServiceError(f"Failed to fetch speech token: {str(e)}")
