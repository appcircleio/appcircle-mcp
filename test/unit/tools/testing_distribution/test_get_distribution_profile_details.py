"""Unit tests for get_distribution_profile_details: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.testing_distribution.get_distribution_profile_details import get_distribution_profile_details

PROFILE_ID = "test-profile-uuid"
SAMPLE_RESPONSE = {
    "data": {
        "id": PROFILE_ID,
        "name": "Demo App Prep",
        "appVersions": [{"id": "av-1", "version": "1.0"}],
        "settings": {"authenticationType": 1, "username": None},
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
async def test_get_distribution_profile_details_success(mocked_api):
    """Returns success envelope with data and meta when API returns profile and pagination."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"]["id"] == PROFILE_ID
    assert result["data"]["name"] == "Demo App Prep"
    assert "appVersions" in result["data"]
    assert "password" not in result["data"].get("settings", {})
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert mocked_api.calls.last.request.url.path == f"/distribution/v2/profiles/{PROFILE_ID}"
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_distribution_profile_details_pagination_params(mocked_api):
    """page and size are passed to API and meta reflects pagination."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json={
            "data": {
                "id": PROFILE_ID,
                "name": "Demo App Prep",
                "appVersions": [{"id": "av-1", "version": "1.0"}],
                "settings": {"authenticationType": 1, "username": None},
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

    result = await get_distribution_profile_details(profile_id=PROFILE_ID, page=2, size=5)

    assert result["success"] is True
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 5
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "2"
    assert params.get("size") == "5"


@pytest.mark.asyncio
async def test_get_distribution_profile_details_excluded_fields(mocked_api):
    """Returned profile does not contain settings.password."""
    response_with_password = {
        "data": {
            "id": PROFILE_ID,
            "name": "Test",
            "appVersions": [],
            "settings": {"authenticationType": 1, "password": "secret"},
        },
        "pagination": {"page": 1, "perPage": 25, "totalCount": 0},
    }
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=response_with_password)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert "settings" in result["data"]
    assert "password" not in result["data"].get("settings", {})


@pytest.mark.asyncio
async def test_get_distribution_profile_details_size_cap(mocked_api):
    """Requested size above 100 is capped at 100 and sent to API."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID, size=200)

    assert result["success"] is True
    # Request is capped at 100; meta.page_size comes from API response (25 in SAMPLE_RESPONSE)
    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_distribution_profile_details_size_min_normalized(mocked_api):
    """Requested size below 1 is normalized to 1."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID, size=0)

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params.get("size") == "1"


@pytest.mark.asyncio
async def test_get_distribution_profile_details_meta_without_pagination(mocked_api):
    """When API returns no pagination or non-dict pagination, meta still has page and page_size."""
    response_no_pagination = {
        "data": {"id": PROFILE_ID, "name": "Profile", "appVersions": []},
    }
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=response_no_pagination)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID, page=2, size=10)

    assert result["success"] is True
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 10
    assert "page_count" not in result["meta"] or result["meta"].get("page_count") is None


@pytest.mark.asyncio
async def test_get_distribution_profile_details_response_profile_key(mocked_api):
    """API can return profile under 'profile' key instead of 'data'; we still return it."""
    response_profile_key = {
        "profile": {
            "id": PROFILE_ID,
            "name": "From profile key",
            "appVersions": [],
            "settings": {},
        },
    }
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json=response_profile_key)
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"]["name"] == "From profile key"
    assert result["data"]["id"] == PROFILE_ID


@pytest.mark.asyncio
async def test_get_distribution_profile_details_response_empty_fallback(mocked_api):
    """When API returns data that is not a dict (e.g. string), we treat as empty profile."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(200, json={"data": "invalid-not-dict"})
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == {}


@pytest.mark.asyncio
async def test_get_distribution_profile_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/distribution/v2/profiles/{PROFILE_ID}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_distribution_profile_details(profile_id=PROFILE_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_distribution_profile_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
