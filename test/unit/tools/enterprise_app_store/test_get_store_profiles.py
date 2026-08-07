"""Unit tests for get_store_profiles: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.enterprise_app_store.get_store_profiles import get_store_profiles

SAMPLE_PROFILES = [
    {"id": "store-uuid-1", "name": "Enterprise iOS"},
    {"id": "store-uuid-2", "name": "Enterprise Android"},
]


@pytest.mark.asyncio
async def test_get_store_profiles_success(mocked_api):
    """Returns success envelope with data and meta when API returns profiles."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_store_profiles()

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["count"] == 2
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_store_profiles_default_pagination(mocked_api):
    """No args sends defaults page=1, size=25."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    await get_store_profiles()

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_store_profiles_pagination_params(mocked_api):
    """page and size are passed to API and reflected in meta."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_store_profiles(page=1, size=10)

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 10
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "10"


@pytest.mark.asyncio
async def test_get_store_profiles_size_cap(mocked_api):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_store_profiles(page=1, size=200)

    assert result["meta"]["page_size"] == 100
    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_store_profiles_filters_and_sort(mocked_api):
    """platform_type, publish_type, visibility, sort, sort_direction are passed to the API and reflected in meta."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(200, json=SAMPLE_PROFILES)
    )

    result = await get_store_profiles(
        platform_type=[1],
        publish_type=[2],
        visibility=False,
        sort=3,
        sort_direction=2,
    )

    assert result["success"] is True
    assert result["meta"]["platform_type"] == [1]
    assert result["meta"]["publish_type"] == [2]
    assert result["meta"]["visibility"] is False
    assert result["meta"]["sort"] == 3
    assert result["meta"]["sort_direction"] == 2
    params = mocked_api.calls.last.request.url.params
    assert params.get_list("platformType") == ["1"]
    assert params.get_list("publishType") == ["2"]
    assert params.get("visibility") == "false"
    assert params.get("sort") == "3"
    assert params.get("sortDirection") == "2"


@pytest.mark.asyncio
async def test_get_store_profiles_invalid_publish_type_returns_validation_error(mocked_api):
    """An unknown publish_type code returns a validation_error without calling the API."""
    result = await get_store_profiles(publish_type=[99])

    assert result["success"] is False
    assert result["error"]["tool"] == "get_store_profiles"
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_store_profiles_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/store/v2/profiles").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_store_profiles()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_store_profiles"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
