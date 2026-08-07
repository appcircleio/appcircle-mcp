"""Unit tests for get_publish_details: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_publish_details import get_publish_details

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"
ENDPOINT = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/publish"

SAMPLE_PUBLISH_DETAILS = {
    "environment": {},
    "directories": ["AC_SOURCE", "AC_OUTPUT_DIR"],
    "publishReportingId": "aaaaaaaa-0003-0000-0000-000000000003",
    "id": "aaaaaaaa-0004-0000-0000-000000000004",
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "profileId": PROFILE_ID,
    "appversionId": APP_VERSION_ID,
    "name": "Default Publish Flow",
    "startedOn": "2025-12-15T13:41:40.0796298+00:00",
    "modifiedOn": "2025-12-15T13:42:34.2064722+00:00",
    "startedBy": "aaaaaaaa-0005-0000-0000-000000000005",
    "modifiedBy": None,
    "completedOn": "2025-12-15T13:42:34.3785278+00:00",
    "status": 0,
    "publishHasWarning": False,
    "syncStatus": 0,
    "steps": [
        {
            "name": "Send to Microsoft Intune",
            "componentType": "appcircle_publish_send_to_intune_ios",
            "id": "aaaaaaaa-0006-0000-0000-000000000006",
            "order": 0,
            "publishId": "aaaaaaaa-0004-0000-0000-000000000004",
            "status": 0,
            "latestLogResourceId": "aaaaaaaa-0007-0000-0000-000000000007",
            "flowStepHistories": [
                {
                    "createdOn": "2025-12-15T13:42:30.2111162+00:00",
                    "logResourceId": "aaaaaaaa-0007-0000-0000-000000000007",
                    "status": 0,
                    "artifacts": [],
                }
            ],
        }
    ],
    "triggerType": 0,
    "marketPlaceType": 4,
}


@pytest.mark.asyncio
async def test_get_publish_details_success(mocked_api):
    """Returns success envelope with data (unwrapped) when API returns publish flow details."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=SAMPLE_PUBLISH_DETAILS))

    result = await get_publish_details(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_PUBLISH_DETAILS
    assert len(result["data"]["steps"]) == 1
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_get_publish_details_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await get_publish_details(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_publish_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_publish_details(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
