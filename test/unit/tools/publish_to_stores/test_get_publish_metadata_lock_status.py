"""Unit tests for get_publish_metadata_lock_status: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_publish_metadata_lock_status import (
    get_publish_metadata_lock_status,
)

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
ENDPOINT = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/metadata/lock"


@pytest.mark.asyncio
async def test_get_publish_metadata_lock_status_unlocked(mocked_api):
    """Returns success envelope with data (unwrapped) when API returns locked: false."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json={"locked": False}))

    result = await get_publish_metadata_lock_status(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == {"locked": False}
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_get_publish_metadata_lock_status_locked(mocked_api):
    """Returns success envelope with data when API returns locked: true."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json={"locked": True}))

    result = await get_publish_metadata_lock_status(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == {"locked": True}


@pytest.mark.asyncio
async def test_get_publish_metadata_lock_status_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await get_publish_metadata_lock_status(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_metadata_lock_status"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_publish_metadata_lock_status_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_publish_metadata_lock_status(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_metadata_lock_status"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
