"""Unit tests for get_build_configuration_details: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_build_configuration_details import get_build_configuration_details

# Mock IDs for tests (no real org/profile/configuration data)
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
CONFIGURATION_ID = "aaaaaaaa-0002-0000-0000-000000000002"

SAMPLE_RESPONSE = {
    "item1": {
        "id": CONFIGURATION_ID,
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "profileId": PROFILE_ID,
        "configurationName": "Default Configuration",
        "platformType": 1,
        "buildPriority": 5,
        "platformSetting": {
            "selectedXcodeVersion": "15.0.x",
            "selectedProject": "./hello_world.xcodeproj",
            "selectedScheme": "hello_world",
        },
        "distributionProfileId": "aaaaaaaa-0003-0000-0000-000000000003",
        "environmentVariables": ["aaaaaaaa-0004-0000-0000-000000000004"],
        "createDate": "2025-02-19T10:03:07.8086637+00:00",
        "updateDate": "2025-10-16T13:26:31.8081284+00:00",
    },
    "item2": {},
}


@pytest.mark.asyncio
async def test_get_build_configuration_details_success(mocked_api):
    """Returns success envelope with data (item1, item2) when API returns configuration."""
    mocked_api.get(
        f"/build/v2/profiles/{PROFILE_ID}/configurations/{CONFIGURATION_ID}"
    ).mock(return_value=Response(200, json=SAMPLE_RESPONSE))

    result = await get_build_configuration_details(
        profile_id=PROFILE_ID, configuration_id=CONFIGURATION_ID
    )

    assert result["success"] is True
    assert "item1" in result["data"]
    assert "item2" in result["data"]
    assert result["data"]["item1"]["id"] == CONFIGURATION_ID
    assert result["data"]["item1"]["profileId"] == PROFILE_ID
    assert result["data"]["item1"]["configurationName"] == "Default Configuration"
    assert result["data"]["item2"] == {}
    assert result["meta"] == {}
    assert (
        mocked_api.calls.last.request.url.path
        == f"/build/v2/profiles/{PROFILE_ID}/configurations/{CONFIGURATION_ID}"
    )


@pytest.mark.asyncio
async def test_get_build_configuration_details_response_passthrough(mocked_api):
    """Full API response is returned in data without modification."""
    mocked_api.get(
        f"/build/v2/profiles/{PROFILE_ID}/configurations/{CONFIGURATION_ID}"
    ).mock(return_value=Response(200, json=SAMPLE_RESPONSE))

    result = await get_build_configuration_details(
        profile_id=PROFILE_ID, configuration_id=CONFIGURATION_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_RESPONSE


@pytest.mark.asyncio
async def test_get_build_configuration_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(
        f"/build/v2/profiles/{PROFILE_ID}/configurations/{CONFIGURATION_ID}"
    ).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_build_configuration_details(
        profile_id=PROFILE_ID, configuration_id=CONFIGURATION_ID
    )

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_build_configuration_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
