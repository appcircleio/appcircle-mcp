"""Unit tests for get_metadata_locales: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_metadata_locales import get_metadata_locales

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"
ENDPOINT = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/metadata/locales"

SAMPLE_LOCALES = [
    {"name": "English (U.S.)", "code": "en-US", "localized": False, "isPrimary": True},
    {"name": "German", "code": "de-DE", "localized": True, "isPrimary": False},
]


@pytest.mark.asyncio
async def test_get_metadata_locales_success(mocked_api):
    """Returns success envelope with data (unwrapped list) and count when API returns locales."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=SAMPLE_LOCALES))

    result = await get_metadata_locales(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOCALES
    assert result["meta"] == {"count": 2}


@pytest.mark.asyncio
async def test_get_metadata_locales_empty_list(mocked_api):
    """API returning an empty list yields an empty data list and count 0."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json=[]))

    result = await get_metadata_locales(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_metadata_locales_wrapper_response(mocked_api):
    """API returning a { data: ... } wrapper is normalized to the underlying list."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(200, json={"data": SAMPLE_LOCALES}))

    result = await get_metadata_locales(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOCALES


@pytest.mark.asyncio
async def test_get_metadata_locales_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(404, json={"message": "Not found"}))

    result = await get_metadata_locales(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_metadata_locales"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_metadata_locales_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(ENDPOINT).mock(return_value=Response(500, json={"message": "Internal server error"}))

    result = await get_metadata_locales(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_metadata_locales"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
