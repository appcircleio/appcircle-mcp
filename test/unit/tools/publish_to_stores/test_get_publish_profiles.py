"""Unit tests for get_publish_profiles: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles

SAMPLE_PROFILES = [
    {"id": "pub-uuid-1", "name": "App Store Release"},
]
SAMPLE_RESPONSE_WITH_PAGINATION = {
    "data": SAMPLE_PROFILES,
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
async def test_get_publish_profiles_success_ios(mocked_api):
    """Returns success envelope with data and meta for platform_type=ios."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE_WITH_PAGINATION)
    )

    result = await get_publish_profiles(platform_type="ios")

    assert result["success"] is True
    assert result["data"] == SAMPLE_PROFILES
    assert result["meta"]["count"] == 1
    assert result["meta"]["platform_type"] == "ios"
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_publish_profiles_success_android(mocked_api):
    """Calls correct endpoint for platform_type=android; data and meta present."""
    mocked_api.get("/publish/v2/profiles/android").mock(
        return_value=Response(200, json={"data": [], "pagination": {"page": 1, "perPage": 25, "totalCount": 0}})
    )

    result = await get_publish_profiles(platform_type="android")

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0
    assert result["meta"]["platform_type"] == "android"
    assert mocked_api.calls.last.request.url.path == "/publish/v2/profiles/android"


@pytest.mark.asyncio
async def test_get_publish_profiles_default_pagination(mocked_api):
    """No page/size sends defaults page=1, size=25."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE_WITH_PAGINATION)
    )

    await get_publish_profiles(platform_type="ios")

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_publish_profiles_pagination_params(mocked_api):
    """page and size are passed to API and reflected in meta."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(200, json={
            "data": SAMPLE_PROFILES,
            "pagination": {
                "page": 2,
                "perPage": 10,
                "pageCount": 1,
                "totalCount": 1,
                "enablePrevious": True,
                "enableNext": False,
            },
        })
    )

    result = await get_publish_profiles(platform_type="ios", page=2, size=10)

    assert result["success"] is True
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 10
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "2"
    assert params.get("size") == "10"


@pytest.mark.asyncio
async def test_get_publish_profiles_flow_status(mocked_api):
    """flow_status (single value) is passed to API as flowStatus and reflected in meta."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE_WITH_PAGINATION)
    )

    result = await get_publish_profiles(platform_type="ios", flow_status=0)

    assert result["success"] is True
    assert result["meta"].get("flow_status") == 0
    params = mocked_api.calls.last.request.url.params
    assert params.get("flowStatus") == "0"


@pytest.mark.asyncio
async def test_get_publish_profiles_size_cap(mocked_api):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(200, json=SAMPLE_RESPONSE_WITH_PAGINATION)
    )

    result = await get_publish_profiles(platform_type="ios", page=1, size=200)

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_publish_profiles_error_returns_unified_envelope(mocked_api):
    """On API error, returns standard error envelope."""
    mocked_api.get("/publish/v2/profiles/ios").mock(
        return_value=Response(404, json={"message": "Not found"})
    )

    result = await get_publish_profiles(platform_type="ios")

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_profiles"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404
