"""Unit tests for get_app_version_metadata: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_app_version_metadata import get_app_version_metadata

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"

SAMPLE_METADATA = {
    "appReviewInformation": {
        "firstName": "user",
        "lastName": "test",
        "phoneNumber": "0000000000",
        "emailAddress": "user@example.com",
        "demoUser": None,
        "demoPassword": "s3cr3t",
        "notes": None,
        "attachmentResourceReferenceId": None,
        "attachmentExtension": None,
        "attachmentFileName": None,
        "attachmentFileSize": None,
    },
    "localizations": [],
    "id": "aaaaaaaa-0003-0000-0000-000000000003",
    "profileId": PROFILE_ID,
    "appVersionId": APP_VERSION_ID,
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "createdByUserId": None,
    "createDate": "2025-11-21T08:47:55.0961967+00:00",
    "updateDate": "2025-11-21T09:27:44.5759905+00:00",
    "releaseInformation": {
        "automaticRelease": False,
        "autoReleaseDate": None,
        "phasedRelease": False,
    },
    "appVersionInformation": {"version": "1.33", "copyright": "not"},
}


@pytest.mark.asyncio
async def test_get_app_version_metadata_success(mocked_api):
    """Returns success envelope with data (unwrapped, demoPassword excluded) when API returns metadata."""
    mocked_api.get(
        f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/metadata"
    ).mock(return_value=Response(200, json=SAMPLE_METADATA))

    result = await get_app_version_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"]["id"] == SAMPLE_METADATA["id"]
    assert result["data"]["appVersionInformation"] == SAMPLE_METADATA["appVersionInformation"]
    assert "demoPassword" not in result["data"]["appReviewInformation"]
    assert result["data"]["appReviewInformation"]["emailAddress"] == "user@example.com"
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_get_app_version_metadata_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404, tool returns standard error envelope."""
    mocked_api.get(
        f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/metadata"
    ).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await get_app_version_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_app_version_metadata"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_app_version_metadata_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(
        f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/metadata"
    ).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_app_version_metadata(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_app_version_metadata"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
