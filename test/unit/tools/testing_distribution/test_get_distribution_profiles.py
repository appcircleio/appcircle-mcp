"""Unit tests for get_distribution_profiles: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.testing_distribution.get_distribution_profiles import get_distribution_profiles

SAMPLE_PROFILES = [
    {"id": "dist-uuid-1", "name": "TestFlight iOS"},
    {"id": "dist-uuid-2", "name": "Internal Android"},
]


@pytest.mark.asyncio
async def test_get_distribution_profiles_success(mocked_api):
    """Returns success envelope with data and meta when API returns profiles."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["count"] == 2
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert result["meta"].get("search_term") is None
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_distribution_profiles_default_pagination(mocked_api):
    """No args or only search sends defaults page=1, size=25."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    await get_distribution_profiles()

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_distribution_profiles_pagination_params(mocked_api):
    """page and size are passed to API and reflected in meta."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_distribution_profiles(page=1, size=10)

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 10
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "10"


@pytest.mark.asyncio
async def test_get_distribution_profiles_size_cap(mocked_api):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_distribution_profiles(page=1, size=200)

    assert result["meta"]["page_size"] == 100
    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_distribution_profiles_success_with_search(mocked_api):
    """Search param is passed to API and reflected in meta."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_distribution_profiles(search="iOS")

    assert result["success"] is True
    assert result["meta"].get("search_term") == "iOS"
    assert mocked_api.calls.last.request.url.params.get("search") == "iOS"


@pytest.mark.asyncio
async def test_get_distribution_profiles_excluded_fields(mocked_api):
    """Returned profiles do not contain settings.password."""
    raw_profile = {
        "id": "dist-uuid-1",
        "name": "Test",
        "settings": {
            "authenticationType": 1,
            "password": "secret",
        },
    }
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json=[raw_profile])
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert len(result["data"]) == 1
    profile = result["data"][0]
    assert profile["id"] == "dist-uuid-1"
    assert profile["name"] == "Test"
    assert "settings" in profile
    assert "password" not in profile.get("settings", {})


@pytest.mark.asyncio
async def test_get_distribution_profiles_response_items_key(mocked_api):
    """API can return list under 'items' key; we use it like 'data'."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json={"items": SAMPLE_PROFILES})
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_get_distribution_profiles_response_profiles_key(mocked_api):
    """API can return list under 'profiles' key; we use it like 'data'."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json={"profiles": SAMPLE_PROFILES})
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_get_distribution_profiles_response_data_not_list(mocked_api):
    """When response is dict but data/items/profiles is not a list, we return empty list."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json={"data": {"invalid": "not a list"}})
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_distribution_profiles_response_not_list_or_dict(mocked_api):
    """When API returns a dict with no data/items/profiles keys, we get empty list from fallback."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(200, json={"pagination": {"page": 1}})
    )

    result = await get_distribution_profiles()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_distribution_profiles_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/distribution/v2/profiles").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_distribution_profiles()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_distribution_profiles"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
