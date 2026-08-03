"""Unit tests for cancel_build: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.cancel_build import cancel_build

TASK_ID = "aaaaaaaa-0001-0000-0000-000000000001"
ENDPOINT = f"/build/v3/queue/{TASK_ID}/cancel"


@pytest.mark.asyncio
async def test_cancel_build_success(mocked_api):
    """Returns success envelope with task_id/cancelled when API returns 200 with no body."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(200, content=b""))

    result = await cancel_build(task_id=TASK_ID)

    assert result["success"] is True
    assert result["data"] == {"task_id": TASK_ID, "cancelled": True}
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_cancel_build_409_maps_to_invalid_state(mocked_api):
    """HTTP 409 (e.g. build already finished) maps to type invalid_state, not http_error."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(409, json={"message": "Build already completed"})
    )

    result = await cancel_build(task_id=TASK_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "cancel_build"
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 409


@pytest.mark.asyncio
async def test_cancel_build_422_maps_to_invalid_state(mocked_api):
    """HTTP 422 maps to type invalid_state."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(422, json={"message": "Cannot cancel"})
    )

    result = await cancel_build(task_id=TASK_ID)

    assert result["success"] is False
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 422


@pytest.mark.asyncio
async def test_cancel_build_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404 (unknown task_id), tool returns standard error envelope."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await cancel_build(task_id=TASK_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "cancel_build"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_cancel_build_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await cancel_build(task_id=TASK_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "cancel_build"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
