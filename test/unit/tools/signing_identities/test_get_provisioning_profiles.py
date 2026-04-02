"""Unit tests for get_provisioning_profiles: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.signing_identities.get_provisioning_profiles import get_provisioning_profiles

# Sample provisioning profiles including fields we pop
SAMPLE_PROFILES_RAW = [
    {
        "id": "pp-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "iOS AppStore",
        "binary": "base64mobileprovision...",
        "metaData": {"uploadedBy": "user@example.com"},
        "certificateThumbPrints": ["AA:BB:CC:DD"],
        "provisionedDevices": ["device-uuid-1", "device-uuid-2"],
        "connectApiKeyId": "key-123",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "pp-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Development",
        "binary": "base64...",
        "metaData": None,
        "certificateThumbPrints": [],
        "provisionedDevices": [],
        "connectApiKeyId": None,
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]

# Expected after trimming (excluded keys removed)
SAMPLE_PROFILES_TRIMMED = [
    {
        "id": "pp-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "iOS AppStore",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "pp-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Development",
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_provisioning_profiles_success_no_app_id(mocked_api):
    """Returns success envelope with data and meta count when no app_id; excluded keys are popped."""
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES_RAW)
    )

    result = await get_provisioning_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES_TRIMMED
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "iOS AppStore"
    assert "binary" not in result["data"][0]
    assert "metaData" not in result["data"][0]
    assert "certificateThumbPrints" not in result["data"][0]
    assert "provisionedDevices" not in result["data"][0]
    assert "connectApiKeyId" not in result["data"][0]
    assert result["meta"]["count"] == 2
    assert "filters" not in result["meta"]
    req = mocked_api.calls.last.request
    assert req.url.path == "/signing-identity/v2/provisioning-profiles"
    assert "appId" not in (req.url.query or "")


@pytest.mark.asyncio
async def test_get_provisioning_profiles_success_with_app_id(mocked_api):
    """Passes appId as query param when app_id provided; meta includes filters."""
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES_RAW)
    )

    result = await get_provisioning_profiles(app_id="com.example.myapp")

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES_TRIMMED
    assert result["meta"]["count"] == 2
    assert result["meta"]["filters"] == {"app_id": "com.example.myapp"}
    req = mocked_api.calls.last.request
    assert req.url.path == "/signing-identity/v2/provisioning-profiles"
    assert "appId=com.example.myapp" in str(req.url)


@pytest.mark.asyncio
async def test_get_provisioning_profiles_empty_list(mocked_api):
    """Returns success with empty data list and count 0 when API returns empty list."""
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
        return_value=Response(200, json=[])
    )

    result = await get_provisioning_profiles()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_provisioning_profiles_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data/provisioningProfiles) is normalized; excluded keys still popped."""
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
        return_value=Response(200, json={"data": SAMPLE_PROFILES_RAW})
    )

    result = await get_provisioning_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES_TRIMMED
    assert result["meta"]["count"] == 2
    for profile in result["data"]:
        assert "binary" not in profile
        assert "metaData" not in profile
        assert "certificateThumbPrints" not in profile
        assert "provisionedDevices" not in profile
        assert "connectApiKeyId" not in profile


@pytest.mark.asyncio
async def test_get_provisioning_profiles_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_provisioning_profiles()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_provisioning_profiles"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
