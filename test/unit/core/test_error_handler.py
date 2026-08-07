"""Unit tests for handle_api_error: envelope shape and exception mapping."""

import pytest
import httpx

from src.core.error_handler import handle_api_error, handle_write_api_error

TOOL_NAME = "test_tool"


def _make_http_status_error(status_code: int, body_message: str = None):
    """Build HTTPStatusError with a minimal response."""
    request = httpx.Request("GET", "https://api.appcircle.io/build/v2/profiles")
    response = httpx.Response(
        status_code,
        json={"message": body_message} if body_message else {},
        request=request,
    )
    return httpx.HTTPStatusError("", request=request, response=response)


def test_handle_api_error_http_status_error_401():
    """HTTP 401 returns envelope with type http_error and status_code."""
    err = _make_http_status_error(401, "Invalid token")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == TOOL_NAME
    assert result["error"]["type"] == "http_error"
    assert result["error"]["message"] == "Unauthorized - Invalid or expired access token"
    assert result["error"]["details"] == "Invalid token"
    assert result["error"]["status_code"] == 401


def test_handle_api_error_http_status_error_404():
    """HTTP 404 returns correct message and status_code."""
    err = _make_http_status_error(404)
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404
    assert "not found" in result["error"]["message"].lower()


def test_handle_api_error_http_status_error_500():
    """HTTP 500 returns correct message and status_code."""
    err = _make_http_status_error(500, "Internal error")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert result["error"]["details"] == "Internal error"


def test_handle_api_error_request_error():
    """RequestError (e.g. connection) returns type request_error, no status_code."""
    err = httpx.ConnectError("Connection refused")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["tool"] == TOOL_NAME
    assert result["error"]["type"] == "request_error"
    assert "connect" in result["error"]["message"].lower() or "Failed" in result["error"]["message"]
    assert "status_code" not in result["error"]


def test_handle_api_error_timeout_exception():
    """TimeoutException returns type timeout_error (not request_error)."""
    err = httpx.ReadTimeout("Timed out")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["tool"] == TOOL_NAME
    assert result["error"]["type"] == "timeout_error"
    assert "timed out" in result["error"]["message"].lower()
    assert "status_code" not in result["error"]


def test_handle_api_error_value_error():
    """ValueError returns type validation_error."""
    err = ValueError("search must be a string")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert result["error"]["details"] == "search must be a string"


def test_handle_api_error_unknown_error():
    """Generic Exception returns type unknown_error."""
    err = RuntimeError("Something broke")
    result = handle_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["tool"] == TOOL_NAME
    assert result["error"]["type"] == "unknown_error"
    assert result["error"]["details"] == "Something broke"


@pytest.mark.parametrize("status_code", [409, 422])
def test_handle_write_api_error_remaps_409_422_to_invalid_state(status_code):
    """409/422 are remapped from http_error to invalid_state for write tools."""
    err = _make_http_status_error(status_code, "Build already running")
    result = handle_write_api_error(err, TOOL_NAME)

    assert result["success"] is False
    assert result["error"]["tool"] == TOOL_NAME
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == status_code
    assert result["error"]["details"] == "Build already running"


def test_handle_write_api_error_leaves_other_http_errors_as_http_error():
    """Non-409/422 HTTP errors (e.g. 401, 500) stay type http_error, not remapped."""
    err = _make_http_status_error(401, "Invalid token")
    result = handle_write_api_error(err, TOOL_NAME)

    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 401


def test_handle_write_api_error_leaves_non_http_errors_unchanged():
    """Non-HTTP exceptions (validation_error, request_error, etc.) pass through unchanged."""
    err = ValueError("bad input")
    result = handle_write_api_error(err, TOOL_NAME)

    assert result["error"]["type"] == "validation_error"
