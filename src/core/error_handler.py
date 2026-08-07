"""Error handling for API operations: map exceptions to the standard error envelope."""

from typing import Any, Dict

import httpx

from src.schemas.responses import error_response


def _get_http_error_message(status_code: int) -> str:
    """User-friendly message for HTTP status codes."""
    messages = {
        400: "Bad request - Invalid parameters provided",
        401: "Unauthorized - Invalid or expired access token",
        403: "Forbidden - You don't have permission to access this resource",
        404: "Not found - The requested resource doesn't exist",
        409: "Conflict - The resource already exists or there's a conflict",
        422: "Unprocessable entity - Invalid data format",
        429: "Too many requests - Rate limit exceeded",
        500: "Internal server error - Appcircle API encountered an error",
        502: "Bad gateway - Appcircle API is temporarily unavailable",
        503: "Service unavailable - Appcircle API is down for maintenance",
        504: "Gateway timeout - Appcircle API took too long to respond",
    }
    return messages.get(status_code, f"HTTP error {status_code} occurred")


def handle_api_error(error: Exception, tool_name: str) -> Dict[str, Any]:
    """
    Map an exception to the standard error envelope.

    Uses the envelope shape from schemas.responses.error_response() so the
    contract lives in one place; this module only handles exception mapping.
    """
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        try:
            body = error.response.json()
            details = body.get("message", str(error))
        except Exception:
            details = error.response.text or str(error)
        return error_response(
            tool=tool_name,
            type="http_error",
            message=_get_http_error_message(status_code),
            details=details,
            status_code=status_code,
        )
    # TimeoutException is a subclass of RequestError; check it first
    if isinstance(error, httpx.TimeoutException):
        return error_response(
            tool=tool_name,
            type="timeout_error",
            message="Request to Appcircle API timed out",
            details=str(error),
        )
    if isinstance(error, httpx.RequestError):
        return error_response(
            tool=tool_name,
            type="request_error",
            message="Failed to connect to Appcircle API",
            details=str(error),
        )
    if isinstance(error, ValueError):
        return error_response(
            tool=tool_name,
            type="validation_error",
            message="Invalid input provided",
            details=str(error),
        )
    return error_response(
        tool=tool_name,
        type="unknown_error",
        message="An unexpected error occurred",
        details=str(error),
    )


INVALID_STATE_STATUS_CODES = frozenset({409, 422})


def handle_write_api_error(error: Exception, tool_name: str) -> Dict[str, Any]:
    """
    Map an exception to the standard error envelope, for write/action tools.

    Same as handle_api_error, except HTTP 409/422 (the API's way of signaling
    the target resource is in a state that doesn't allow this action, e.g. a
    build already in progress) are remapped from type "http_error" to
    "invalid_state" so callers can distinguish "retry won't help without a
    state change" from a generic HTTP failure.
    """
    result = handle_api_error(error, tool_name)
    error_detail = result.get("error", {})
    if error_detail.get("type") == "http_error" and error_detail.get("status_code") in INVALID_STATE_STATUS_CODES:
        error_detail["type"] = "invalid_state"
    return result
