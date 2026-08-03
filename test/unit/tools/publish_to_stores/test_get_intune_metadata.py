"""Unit tests for get_intune_metadata: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_intune_metadata import get_intune_metadata

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"
ENDPOINT = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/intune/metadata"

SAMPLE_INTUNE_METADATA = {
    "id": "aaaaaaaa-0003-0000-0000-000000000003",
    "profileId": PROFILE_ID,
    "appVersionId": APP_VERSION_ID,
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "createdByUserId": "aaaaaaaa-0004-0000-0000-000000000004",
    "createDate": "2025-12-15T13:07:40.2005232+00:00",
    "updateDate": "2025-12-15T13:42:49.1307667+00:00",
    "platformType": 1,
    "intuneAppId": "aaaaaaaa-0005-0000-0000-000000000005",
    "displayName": "Test App",
    "description": "Test application.",
    "publisher": "Acme",
    "intuneCreatedDateTime": "2025-12-15T12:43:49.067Z",
    "intuneLastModifiedDateTime": "2025-12-15T13:42:33.515Z",
    "isFeatured": False,
    "privacyInformationUrl": "https://example.com/privacy-policy",
    "informationUrl": "https://example.com",
    "owner": "Acme",
    "developer": "Acme",
    "notes": "",
    "publishingState": "published",
    "committedContentVersion": "4",
    "bundleId": "com.example.app",
    "expirationDateTime": "2026-03-04T10:45:58Z",
    "version": "1.0",
    "versionCode": "1",
    "applicableDeviceType": {"iPad": True, "iPhoneAndIPod": True},
    "minimumSupportedOperatingSystem": "v8_0",
    "categories": [{"id": "aaaaaaaa-0006-0000-0000-000000000006", "displayName": "Business"}],
    "targetedPlatforms": None,
}


@pytest.mark.asyncio
async def test_get_intune_metadata_success(mocked_api):
    """Returns success envelope with data (unwrapped) when API returns Intune metadata."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=SAMPLE_INTUNE_METADATA))

    result = await get_intune_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_INTUNE_METADATA
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_get_intune_metadata_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await get_intune_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_intune_metadata"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_intune_metadata_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_intune_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_intune_metadata"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
