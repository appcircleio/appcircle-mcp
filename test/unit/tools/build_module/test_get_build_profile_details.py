"""Unit tests for get_build_profile_details: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_build_profile_details import get_build_profile_details

SAMPLE_PROFILE = {
    "id": "test-profile-uuid",
    "name": "iOS Production",
    "buildPlatformType": 1,
}


@pytest.mark.asyncio
async def test_get_build_profile_details_success(mocked_api):
    """Returns success envelope with data when API returns a profile."""
    profile_id = "test-profile-uuid"
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(200, json=SAMPLE_PROFILE)
    )

    result = await get_build_profile_details(profile_id=profile_id)

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILE
    assert result["data"]["id"] == profile_id
    assert mocked_api.calls.last.request.url.path == f"/build/v2/profiles/{profile_id}"


@pytest.mark.asyncio
async def test_get_build_profile_details_excluded_fields(mocked_api):
    """Returned profile does not contain connectionEnvironmentKey or webhookSecret."""
    profile_id = "test-profile-uuid"
    raw_profile = {
        "id": profile_id,
        "name": "Test",
        "buildPlatformType": 1,
        "connectionEnvironmentKey": "env-secret",
        "webhookSecret": "whisper-secret",
    }
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(200, json=raw_profile)
    )

    result = await get_build_profile_details(profile_id=profile_id)

    assert result["success"] is True
    assert result["data"]["id"] == profile_id
    assert result["data"]["name"] == "Test"
    assert "connectionEnvironmentKey" not in result["data"]
    assert "webhookSecret" not in result["data"]


@pytest.mark.asyncio
async def test_get_build_profile_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    profile_id = "test-profile-uuid"
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_build_profile_details(profile_id=profile_id)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_build_profile_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]


@pytest.mark.asyncio
async def test_get_build_profile_details_without_configurations_does_not_call_configurations_endpoint(
    mocked_api,
):
    """When configurations is False (default), only profile endpoint is called."""
    profile_id = "test-profile-uuid"
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(200, json=SAMPLE_PROFILE)
    )

    result = await get_build_profile_details(profile_id=profile_id, configurations=False)

    assert result["success"] is True
    assert "configurations" not in result["data"]
    assert len(mocked_api.calls) == 1
    assert mocked_api.calls.last.request.url.path == f"/build/v2/profiles/{profile_id}"


@pytest.mark.asyncio
async def test_get_build_profile_details_with_configurations_true(mocked_api):
    """When configurations=True, both profile and configurations endpoints are called; data has configurations."""
    profile_id = "test-profile-uuid"
    sample_configurations = [
        {"id": "config-uuid-1", "configurationName": "Default", "profileId": profile_id},
        {"id": "config-uuid-2", "configurationName": "Release", "profileId": profile_id},
    ]
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(200, json=SAMPLE_PROFILE)
    )
    mocked_api.get(f"/build/v2/profiles/{profile_id}/configurations").mock(
        return_value=Response(200, json=sample_configurations)
    )

    result = await get_build_profile_details(profile_id=profile_id, configurations=True)

    assert result["success"] is True
    assert result["data"]["id"] == profile_id
    assert "configurations" in result["data"]
    assert result["data"]["configurations"] == sample_configurations
    assert len(result["data"]["configurations"]) == 2
    assert len(mocked_api.calls) == 2
    paths = [c.request.url.path for c in mocked_api.calls]
    assert f"/build/v2/profiles/{profile_id}" in paths
    assert f"/build/v2/profiles/{profile_id}/configurations" in paths


@pytest.mark.asyncio
async def test_get_build_profile_details_configurations_wrapper_response(mocked_api):
    """Configurations endpoint returning a wrapper (e.g. data/configurations) is normalized to a list."""
    profile_id = "test-profile-uuid"
    mocked_api.get(f"/build/v2/profiles/{profile_id}").mock(
        return_value=Response(200, json=SAMPLE_PROFILE)
    )
    mocked_api.get(f"/build/v2/profiles/{profile_id}/configurations").mock(
        return_value=Response(200, json={"data": [{"id": "c1", "configurationName": "Default"}]})
    )

    result = await get_build_profile_details(profile_id=profile_id, configurations=True)

    assert result["success"] is True
    assert result["data"]["configurations"] == [{"id": "c1", "configurationName": "Default"}]
