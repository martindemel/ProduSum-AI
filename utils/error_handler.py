import logging
import traceback
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

def handle_openai_error(e: Exception) -> Tuple[str, Dict[str, Any]]:
    """
    Handle OpenAI API errors with user-friendly messages
    
    Args:
        e: The exception from OpenAI API
        
    Returns:
        Tuple containing user-friendly error message and error details
    """
    # Convert exception to string
    error_str = str(e).lower()
    # Get error type name if available
    error_type = type(e).__name__
    
    error_details = {
        "original_error": str(e),
        "error_type_name": error_type
    }
    
    # Check for newer API error types first (OpenAI v1.x)
    if "apiconnectionerror" in error_type:
        message = "Could not connect to the OpenAI API. Please check your internet connection."
        error_details["error_type"] = "connection_error"
        logger.error(f"OpenAI API connection error: {e}")
    elif "apiconnectionerror" in error_type or "connection" in error_str:
        message = "Could not connect to the OpenAI API. Please check your internet connection."
        error_details["error_type"] = "connection_error"
        logger.error(f"OpenAI API connection error: {e}")
    elif "ratecreaterequesterror" in error_type or "rate_limit" in error_str or "rate limit" in error_str or "too many requests" in error_str:
        message = "API rate limit exceeded. Please try again in a few minutes."
        error_details["error_type"] = "rate_limit"
        logger.warning(f"Rate limit error: {e}")
    elif "authenticationerror" in error_type or "authentication" in error_str or "auth" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
        message = "Authentication error. Please check your OpenAI API key."
        error_details["error_type"] = "authentication"
        logger.error(f"Authentication error: {e}")
    elif "insufficientquota" in error_type or "quota" in error_str or "billing" in error_str:
        message = "Your OpenAI API quota has been exceeded. Please check your billing details."
        error_details["error_type"] = "quota_exceeded"
        logger.error(f"Quota exceeded error: {e}")
    elif "invalidrequesterror" in error_type or "invalid_request" in error_str or "bad request" in error_str or "validation" in error_str:
        message = "Invalid request. Please check your inputs and try again."
        error_details["error_type"] = "invalid_request"
        logger.warning(f"Invalid request error: {e}")
    elif "apierror" in error_type and ("model" in error_str or "not found" in error_str or "unavailable" in error_str):
        message = "The requested AI model is currently unavailable."
        error_details["error_type"] = "model_error"
        logger.error(f"Model error: {e}")
    elif "contentfilterror" in error_type or "content_filter" in error_str or "content filter" in error_str or "policy" in error_str or "safety" in error_str:
        message = "Your request was flagged by content filters. Please modify your content and try again."
        error_details["error_type"] = "content_filter"
        logger.warning(f"Content filter error: {e}")
    elif "timeout" in error_str or "timed out" in error_str:
        message = "The request timed out. Please try again with simpler inputs."
        error_details["error_type"] = "timeout"
        logger.warning(f"Timeout error: {e}")
    # Generic error fallback
    else:
        message = "An error occurred with the AI service. Please try again later."
        error_details["error_type"] = "unknown"
        logger.error(f"Unexpected OpenAI error: {e}\n{traceback.format_exc()}")
    
    return message, error_details

def log_error(error_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an error with consistent formatting
    
    Args:
        error_type: The type of error (e.g., "openai", "validation")
        message: The error message
        details: Additional error details
    """
    details = details or {}
    
    # Log with appropriate level based on error type
    if error_type in ["authentication", "server", "critical"]:
        logger.error(f"{error_type.upper()} ERROR: {message} | Details: {details}")
    elif error_type in ["rate_limit", "timeout", "invalid_request"]:
        logger.warning(f"{error_type.upper()} WARNING: {message} | Details: {details}")
    else:
        logger.info(f"{error_type.upper()} INFO: {message} | Details: {details}") 