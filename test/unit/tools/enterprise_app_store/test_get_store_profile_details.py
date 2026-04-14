"""Unit tests for get_store_profile_details: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.enterprise_app_store.get_store_profile_details import get_store_profile_details

PROFILE_ID = "test-store-profile-uuid"
SAMPLE_RESPONSE = {
    "data": {
        "id": PROFILE_ID,
        "name": "Enterprise iOS",
        "appVersions": [{"id": "av-1", "version": "1.0"}],
    },
    "pagination": {
        "page": 1,
        "perPage": 25,
        "pageCount": 1,
        "totalCount": 1,
        "enablePrevious": False,
        "enableNext": False,
    },
}


@pytest.mark.asyncio
async def test_get_store_profile_details_success(mocked_api):
    """Returns success envelope with data and meta when API returns profile and pagination."""
    mocked_api.get(f"/store/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE)
    )

    result = await get_store_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"]["id"] == PROFILE_ID
    assert result["data"]["name"] == "Enterprise iOS"
    assert "appVersions" in result["data"]
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert mocked_api.calls.last.request.url.path == f"/store/v2/profiles/{PROFILE_ID}"
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_store_profile_details_pagination_params(mocked_api):
    """page and size are passed to API and meta reflects pagination."""
    mocked_api.get(f"/store/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json={
            "data": {
                "id": PROFILE_ID,
                "name": "Enterprise iOS",
                "appVersions": [{"id": "av-1", "version": "1.0"}],
            },
            "pagination": {
                "page": 2,
                "perPage": 5,
                "pageCount": 1,
                "totalCount": 1,
                "enablePrevious": True,
                "enableNext": False,
            },
        })
    )

    result = await get_store_profile_details(profile_id=PROFILE_ID, page=2, size=5)

    assert result["success"] is True
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 5
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "2"
    assert params.get("size") == "5"


@pytest.mark.asyncio
async def test_get_store_profile_details_excluded_fields(mocked_api):
    """Returned profile and app versions do not contain signedCertThumbPrint."""
    response_with_thumb = {
        "data": {
            "id": PROFILE_ID,
            "name": "Test",
            "signedCertThumbPrint": "thumb-on-profile",
            "appVersions": [
                {"id": "av-1", "version": "1.0", "signedCertThumbPrint": "thumb-on-av"},
            ],
        },
        "pagination": {"page": 1, "perPage": 25, "totalCount": 1},
    }
    mocked_api.get(f"/store/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=response_with_thumb)
    )

    result = await get_store_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert "signedCertThumbPrint" not in result["data"]
    assert len(result["data"]["appVersions"]) == 1
    assert "signedCertThumbPrint" not in result["data"]["appVersions"][0]


@pytest.mark.asyncio
async def test_get_store_profile_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/store/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_store_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_store_profile_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
