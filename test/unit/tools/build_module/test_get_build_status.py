"""Unit tests for get_build_status: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_build_status import get_build_status

# Mock IDs for tests (no real commit/build data)
COMMIT_ID = "aaaaaaaa-0001-0000-0000-000000000001"
BUILD_ID = "aaaaaaaa-0002-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_get_build_status_success(mocked_api):
    """Returns success envelope with the raw status code."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/status").mock(
        return_value=Response(200, json={"status": 0})
    )

    result = await get_build_status(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is True
    assert result["data"] == {"status": 0}
    assert result["meta"] == {}
    assert (
        mocked_api.calls.last.request.url.path
        == f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/status"
    )


@pytest.mark.asyncio
async def test_get_build_status_running(mocked_api):
    """Passes through in-progress status codes unchanged (e.g. 91=Running)."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/status").mock(
        return_value=Response(200, json={"status": 91})
    )

    result = await get_build_status(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is True
    assert result["data"] == {"status": 91}


@pytest.mark.asyncio
async def test_get_build_status_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404 (unknown commit/build), tool returns standard error envelope."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/status").mock(
        return_value=Response(404, json={"message": "Not found"})
    )

    result = await get_build_status(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_status"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_build_status_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/status").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_build_status(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_build_status"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
