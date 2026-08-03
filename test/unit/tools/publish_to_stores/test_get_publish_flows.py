"""Unit tests for get_publish_flows: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_publish_flows import get_publish_flows

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
ENDPOINT = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/publishflows"

SAMPLE_FLOWS = [
    {
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "profileId": PROFILE_ID,
        "flowName": "Default Publish Flow",
        "flowDocument": "steps:\n- id: aaaaaaaa-0002-0000-0000-000000000002\n  stepName: Send to Microsoft Intune\n",
        "id": "aaaaaaaa-0003-0000-0000-000000000003",
        "events": [],
    }
]


@pytest.mark.asyncio
async def test_get_publish_flows_success(mocked_api):
    """Returns success envelope with data (unwrapped list) and count when API returns flows."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=SAMPLE_FLOWS))

    result = await get_publish_flows(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_FLOWS
    assert result["meta"] == {"count": 1}


@pytest.mark.asyncio
async def test_get_publish_flows_empty_list(mocked_api):
    """API returning an empty list yields an empty data list and count 0."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=[]))

    result = await get_publish_flows(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_publish_flows_wrapper_response(mocked_api):
    """API returning a { data: ... } wrapper is normalized to the underlying list."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json={"data": SAMPLE_FLOWS}))

    result = await get_publish_flows(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_FLOWS


@pytest.mark.asyncio
async def test_get_publish_flows_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_publish_flows(platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_flows"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
