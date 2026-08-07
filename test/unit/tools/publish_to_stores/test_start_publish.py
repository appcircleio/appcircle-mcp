"""Unit tests for start_publish: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.start_publish import start_publish

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
PUBLISH_ID = "aaaaaaaa-0002-0000-0000-000000000002"
STEP_ID = "aaaaaaaa-0003-0000-0000-000000000003"
ENDPOINT = f"/publish/v3/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/publish/{PUBLISH_ID}/start"
TASK_ID = "aaaaaaaa-0004-0000-0000-000000000004"


@pytest.mark.asyncio
async def test_start_publish_success(mocked_api):
    """Returns success envelope with task_id when API returns a bare JSON string."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(200, json=TASK_ID))

    result = await start_publish(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID)

    assert result["success"] is True
    assert result["data"] == {"task_id": TASK_ID}
    assert result["meta"]["step_id"] is None
    assert result["meta"]["organization_pool_id"] is None


@pytest.mark.asyncio
async def test_start_publish_with_step_id(mocked_api):
    """step_id is passed as a stepId query param and reflected in meta."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(200, json=TASK_ID))

    result = await start_publish(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID, step_id=STEP_ID
    )

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params["stepId"] == STEP_ID
    assert result["meta"]["step_id"] == STEP_ID


@pytest.mark.asyncio
async def test_start_publish_with_organization_pool_id(mocked_api):
    """organization_pool_id is passed as an organizationPoolId query param."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(200, json=TASK_ID))

    result = await start_publish(
        platform_type=PLATFORM_TYPE,
        profile_id=PROFILE_ID,
        publish_id=PUBLISH_ID,
        organization_pool_id="pool-uuid",
    )

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params["organizationPoolId"] == "pool-uuid"
    assert result["meta"]["organization_pool_id"] == "pool-uuid"


@pytest.mark.asyncio
async def test_start_publish_409_maps_to_invalid_state(mocked_api):
    """HTTP 409 maps to type invalid_state, not http_error."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(409, json={"message": "Publish already running"})
    )

    result = await start_publish(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "start_publish"
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 409


@pytest.mark.asyncio
async def test_start_publish_422_maps_to_invalid_state(mocked_api):
    """HTTP 422 maps to type invalid_state."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(422, json={"message": "Cannot start"}))

    result = await start_publish(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID)

    assert result["success"] is False
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 422


@pytest.mark.asyncio
async def test_start_publish_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await start_publish(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "start_publish"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
