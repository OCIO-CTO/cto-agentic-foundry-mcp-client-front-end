"""
Authentication utilities for the MCP Proxy Server.
"""
from typing import Optional
from fastapi import Header, HTTPException
from config import config
import logging

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Verify API key if configured.

    Args:
        x_api_key: API key from request header

    Returns:
        The API key or "development" if no key is configured

    Raises:
        HTTPException: If API key is required but invalid
    """
    if config.API_KEY and x_api_key != config.API_KEY:
        logger.warning(f"Invalid API key attempt from header")
        raise HTTPException(status_code=401, detail="Invalid API key")

    return x_api_key or "development"


def validate_api_key_sync(api_key: Optional[str]) -> bool:
    """
    Synchronous API key validation.

    Args:
        api_key: API key to validate

    Returns:
        True if valid or not required, False otherwise
    """
    if not config.API_KEY:
        return True
    return api_key == config.API_KEY
