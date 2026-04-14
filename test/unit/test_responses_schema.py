"""Unit tests for standard response envelope (success_response, error shape)."""

from src.schemas.responses import (
    ToolErrorDetail,
    ToolErrorResponse,
    ToolSuccessResponse,
    success_response,
)


def test_success_response_returns_standard_envelope():
    data = [{"id": "1", "name": "Profile A"}]
    result = success_response(data)

    assert result["success"] is True
    assert result["data"] == data
    assert result["meta"] == {}


def test_success_response_with_meta():
    data = []
    meta = {"count": 0, "search_term": "iOS"}
    result = success_response(data, meta=meta)

    assert result["success"] is True
    assert result["data"] == data
    assert result["meta"] == meta


def test_success_response_meta_defaults_to_empty():
    result = success_response({"key": "value"}, meta=None)
    assert result["meta"] == {}


def test_tool_success_response_model_validates():
    payload = ToolSuccessResponse(data=[1, 2, 3], meta={"count": 3})
    assert payload.success is True
    assert payload.data == [1, 2, 3]
    assert payload.meta == {"count": 3}


def test_tool_error_detail_matches_handle_api_error_shape():
    detail = ToolErrorDetail(
        tool="get_build_profiles",
        type="http_error",
        message="Unauthorized",
        details="Invalid token",
        status_code=401,
    )
    d = detail.model_dump()
    assert d["tool"] == "get_build_profiles"
    assert d["type"] == "http_error"
    assert d["status_code"] == 401


def test_tool_error_response_model():
    err = ToolErrorResponse(
        error=ToolErrorDetail(
            tool="get_build_profiles",
            type="validation_error",
            message="Invalid input",
            details="search must be a string",
        )
    )
    assert err.success is False
    assert err.error.type == "validation_error"
