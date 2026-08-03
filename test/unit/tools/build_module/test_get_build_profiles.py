"""Unit tests for get_build_profiles: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_build_profiles import get_build_profiles


@pytest.mark.asyncio
async def test_get_build_profiles_success(mocked_api, sample_build_profiles):
    """Returns success envelope with data and meta when API returns profiles."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    result = await get_build_profiles()

    assert result["success"] is True
    assert result["data"] == sample_build_profiles
    assert result["meta"]["count"] == 2
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert result["meta"].get("search_term") is None
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_build_profiles_default_pagination(mocked_api, sample_build_profiles):
    """No args or only search sends defaults page=1, size=25."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    await get_build_profiles()

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_build_profiles_pagination_params(mocked_api, sample_build_profiles):
    """page and size are passed to API and reflected in meta."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    result = await get_build_profiles(page=1, size=10)

    assert result["success"] is True
    assert result["data"] == sample_build_profiles
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 10
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.params.get("page") == "1"
    assert mocked_api.calls.last.request.url.params.get("size") == "10"


@pytest.mark.asyncio
async def test_get_build_profiles_size_cap(mocked_api, sample_build_profiles):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    result = await get_build_profiles(page=1, size=200)

    assert result["meta"]["page_size"] == 100
    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_build_profiles_success_with_search(mocked_api, sample_build_profiles):
    """Search param is passed to API and reflected in meta."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    result = await get_build_profiles(search="iOS")

    assert result["success"] is True
    assert result["meta"].get("search_term") == "iOS"
    assert mocked_api.calls.last.request.url.params.get("search") == "iOS"


@pytest.mark.asyncio
async def test_get_build_profiles_excluded_fields(mocked_api):
    """Returned profiles do not contain connectionEnvironmentKey or webhookSecret."""
    raw_profile = {
        "id": "profile-uuid-1",
        "name": "Test",
        "buildPlatformType": 1,
        "connectionEnvironmentKey": "env-secret",
        "webhookSecret": "whisper-secret",
    }
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=[raw_profile])
    )

    result = await get_build_profiles()

    assert result["success"] is True
    assert len(result["data"]) == 1
    profile = result["data"][0]
    assert profile["id"] == "profile-uuid-1"
    assert profile["name"] == "Test"
    assert "connectionEnvironmentKey" not in profile
    assert "webhookSecret" not in profile


@pytest.mark.asyncio
async def test_get_build_profiles_filters_and_sort(mocked_api, sample_build_profiles):
    """platform, last_build_status, repository_source, sort, sort_direction are passed to the API and reflected in meta."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(200, json=sample_build_profiles)
    )

    result = await get_build_profiles(
        platform=[1, 2],
        last_build_status=[0, 1],
        repository_source=[1],
        sort=2,
        sort_direction=2,
    )

    assert result["success"] is True
    assert result["meta"]["platform"] == [1, 2]
    assert result["meta"]["last_build_status"] == [0, 1]
    assert result["meta"]["repository_source"] == [1]
    assert result["meta"]["sort"] == 2
    assert result["meta"]["sort_direction"] == 2
    params = mocked_api.calls.last.request.url.params
    assert params.get_list("platform") == ["1", "2"]
    assert params.get_list("lastBuildStatus") == ["0", "1"]
    assert params.get_list("repositorySource") == ["1"]
    assert params.get("sort") == "2"
    assert params.get("sortDirection") == "2"


@pytest.mark.asyncio
async def test_get_build_profiles_invalid_platform_returns_validation_error(mocked_api):
    """An unknown platform code returns a validation_error without calling the API."""
    result = await get_build_profiles(platform=[99])

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_profiles"
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_build_profiles_invalid_sort_returns_validation_error(mocked_api):
    """An unknown sort code returns a validation_error without calling the API."""
    result = await get_build_profiles(sort=99)

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_build_profiles_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/build/v2/profiles").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_build_profiles()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_build_profiles"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
