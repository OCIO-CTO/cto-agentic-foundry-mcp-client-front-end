"""
Custom exceptions and error handling utilities.
"""
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MCPProxyException(Exception):
    """Base exception for MCP Proxy errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(MCPProxyException):
    """Configuration is invalid or missing"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


class AuthenticationError(MCPProxyException):
    """Authentication failed"""
    def __init__(self, message: str = "Invalid API key", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, details=details)


class ValidationError(MCPProxyException):
    """Request validation failed"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, details=details)


class RequestTooLargeError(MCPProxyException):
    """Request body exceeds size limit"""
    def __init__(self, max_size: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Request too large. Maximum size: {max_size} bytes",
            status_code=413,
            details=details
        )


class ToolExecutionError(MCPProxyException):
    """Tool execution failed"""
    def __init__(self, tool_name: str, error: str, details: Optional[Dict[str, Any]] = None):
        message = f"Tool '{tool_name}' execution failed: {error}"
        super().__init__(message, status_code=500, details=details)


class SpeechServiceError(MCPProxyException):
    """Speech service error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, details=details)


def log_error(error: Exception, context: str = "") -> None:
    """
    Log error with context information

    Args:
        error: The exception to log
        context: Additional context about where/when the error occurred
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if context:
        logger.error(f"{context} - {error_type}: {error_msg}")
    else:
        logger.error(f"{error_type}: {error_msg}")

    # Log stack trace for non-MCPProxyException errors
    if not isinstance(error, MCPProxyException):
        logger.exception("Stack trace:")
