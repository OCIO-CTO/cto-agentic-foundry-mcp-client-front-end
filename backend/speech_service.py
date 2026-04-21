"""
Azure Speech Services Integration Module
Provides text-to-speech and speech-to-text functionality
"""
import os
import logging
from typing import Optional
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
    logger.warning("Azure Speech Services credentials not configured")


def get_speech_config() -> speechsdk.SpeechConfig:
    """
    Create and return Azure Speech SDK configuration

    Returns:
        speechsdk.SpeechConfig: Configured speech config object

    Raises:
        ValueError: If credentials are not configured
    """
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise ValueError("Azure Speech Services credentials not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
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
        ValueError: If credentials not configured or synthesis fails
    """
    try:
        speech_config = get_speech_config()

        # Set voice if specified
        if voice_name:
            speech_config.speech_synthesis_voice_name = voice_name
        else:
            speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"

        # Create synthesizer with no audio output (we'll capture bytes)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=None  # None means in-memory result
        )

        logger.info(f"Synthesizing speech for text: {text[:50]}...")
        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(f"Speech synthesis completed, audio size: {len(result.audio_data)} bytes")
            return result.audio_data
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            logger.error(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Error details: {cancellation_details.error_details}")
                raise ValueError(f"Speech synthesis failed: {cancellation_details.error_details}")
            raise ValueError(f"Speech synthesis canceled: {cancellation_details.reason}")
        else:
            raise ValueError(f"Unexpected synthesis result: {result.reason}")

    except Exception as e:
        logger.error(f"Error in speech synthesis: {str(e)}")
        raise


def get_speech_token() -> dict:
    """
    Generate an authentication token for frontend Speech SDK usage
    Token is valid for 10 minutes

    Returns:
        dict: Contains 'token' and 'region' keys

    Raises:
        ValueError: If credentials not configured or token fetch fails
    """
    try:
        if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
            raise ValueError("Azure Speech Services credentials not configured")

        # For Azure Speech Services, we can return the key directly for token exchange
        # The frontend SDK will exchange this for a proper token
        # In production, you might want to call the token endpoint directly
        import httpx

        token_url = f"https://{AZURE_SPEECH_REGION}.api.cognitive.microsoft.us/sts/v1.0/issueToken"
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY
        }

        logger.info(f"Fetching speech token from: {token_url}")

        with httpx.Client(timeout=10.0) as client:
            response = client.post(token_url, headers=headers)
            response.raise_for_status()

            token = response.text
            logger.info("Successfully obtained speech token")

            return {
                "token": token,
                "region": AZURE_SPEECH_REGION
            }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching speech token: {str(e)}")
        raise ValueError(f"Failed to fetch speech token: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching speech token: {str(e)}")
        raise
