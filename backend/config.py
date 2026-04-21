"""
Configuration management for the MCP Proxy Server.
Centralizes environment variable loading and validation.
"""
import os
from typing import List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()


class Config:
    """Application configuration with validation"""

    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    # Azure Speech Configuration
    AZURE_SPEECH_KEY: str = os.getenv("AZURE_SPEECH_KEY", "")
    AZURE_SPEECH_REGION: str = os.getenv("AZURE_SPEECH_REGION", "")

    # MCP Configuration
    REMOTE_MCP_URL: str = os.getenv(
        "REMOTE_MCP_URL",
        "https://fsis-mcp-server-test1.azurewebsites.us/mcp"
    )

    # Server Configuration
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3001").split(",")
    ]

    # Security Configuration
    API_KEY: str = os.getenv("API_KEY", "")

    # Performance Configuration
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))
    MAX_TOOL_ITERATIONS: int = int(os.getenv("MAX_TOOL_ITERATIONS", "10"))
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "10/minute")
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "1048576"))

    # Validation limits
    MAX_MESSAGES_PER_REQUEST: int = 100
    MAX_TEXT_LENGTH_FOR_TTS: int = 10000

    @classmethod
    def validate_azure_openai(cls) -> bool:
        """Validate Azure OpenAI configuration"""
        if not cls.AZURE_OPENAI_API_KEY:
            logger.error("AZURE_OPENAI_API_KEY not set")
            return False
        if not cls.AZURE_OPENAI_ENDPOINT:
            logger.error("AZURE_OPENAI_ENDPOINT not set")
            return False
        return True

    @classmethod
    def validate_azure_speech(cls) -> bool:
        """Validate Azure Speech configuration"""
        if not cls.AZURE_SPEECH_KEY or not cls.AZURE_SPEECH_REGION:
            logger.warning("Azure Speech Services credentials not configured")
            return False
        return True

    @classmethod
    def validate_all(cls) -> bool:
        """Validate all required configuration"""
        is_valid = cls.validate_azure_openai()

        # Speech is optional, just log warning
        cls.validate_azure_speech()

        return is_valid


# Create singleton config instance
config = Config()

# Validate configuration on module load
if not config.validate_all():
    logger.error("Configuration validation failed. Please check environment variables.")
