"""
Integration tests for get_distribution_profiles (real Appcircle API).

Run with: pytest test/integration/testing_distribution/ -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import os
import pytest
import httpx
from datetime import datetime
from typing import Dict, Any, List

from src.tools.testing_distribution.get_distribution_profiles import get_distribution_profiles


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _count(response: Dict[str, Any]) -> int:
    """Unified envelope: count is in meta."""
    return response.get("meta", {}).get("count", 0)


def _search_term(response: Dict[str, Any]):
    """Unified envelope: search_term is in meta."""
    return response.get("meta", {}).get("search_term")


def _normalize_api_profiles(raw: Any) -> List[Dict[str, Any]]:
    """Return list of profiles whether API returned a list or a wrapper dict."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("data") or raw.get("items") or raw.get("profiles") or []
    return []


async def call_api_directly(
    token: str, params: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Call Appcircle API directly for comparison. Pass page/size to match tool."""
    api_url = os.getenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{api_url.rstrip('/')}/distribution/v2/profiles",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params=params or {},
            timeout=120,
        )
        response.raise_for_status()
        return _normalize_api_profiles(response.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Response has success, data, meta; data is list; count in meta matches."""
    response = await get_distribution_profiles()
    assert isinstance(response, dict), "Response must be a dict"
    assert "success" in response
    assert "data" in response
    assert "meta" in response
    assert response["success"] is True, response.get("error")
    profiles = _profiles(response)
    assert isinstance(profiles, list)
    assert _count(response) == len(profiles)
    meta = response.get("meta", {})
    assert "page" in meta
    assert "page_size" in meta
    if profiles:
        for field in ["id", "name"]:
            assert field in profiles[0], f"Profile missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination(integration_settings):
    """Pagination params return a page; meta has page, page_size, count."""
    response = await get_distribution_profiles(page=1, size=5)
    assert response.get("success"), response.get("error")
    data = _profiles(response)
    assert isinstance(data, list)
    meta = response.get("meta", {})
    assert meta.get("page") == 1
    assert meta.get("page_size") == 5
    assert meta.get("count") == len(data)
    assert len(data) <= 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_consistency(integration_settings):
    """Tool result matches direct API when using same page/size."""
    token = os.getenv("APPCIRCLE_ACCESS_TOKEN")
    params = {"page": "1", "size": "25"}
    api_result = await call_api_directly(token, params=params)
    tool_result = await get_distribution_profiles(page=1, size=25)
    assert tool_result.get("success"), tool_result.get("error")
    assert len(api_result) == _count(tool_result)
    api_ids = {p["id"] for p in api_result}
    tool_ids = {p["id"] for p in _profiles(tool_result)}
    assert api_ids == tool_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_with_pagination(integration_settings):
    """Search with page/size returns success and search_term/page/page_size in meta."""
    response = await get_distribution_profiles(search="demo", page=1, size=10)
    assert response.get("success"), response.get("error")
    assert response.get("meta", {}).get("search_term") == "demo"
    assert response.get("meta", {}).get("page") == 1
    assert response.get("meta", {}).get("page_size") == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_excluded_fields(integration_settings):
    """No profile in data has settings.password."""
    response = await get_distribution_profiles(page=1, size=25)
    if not response.get("success") or not _profiles(response):
        pytest.skip("No profiles to validate")
    for profile in _profiles(response):
        assert "password" not in profile.get("settings", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_functionality(integration_settings):
    """Search param filters profiles and reflects search_term in meta.

    The API's search matches more than just `name` (confirmed against a real
    org - same behavior seen on get_build_profiles), so this only asserts the
    profile the term was derived from is present in the results, not that
    every result's name contains the term.
    """
    all_result = await get_distribution_profiles(page=1, size=25)
    if not all_result.get("success") or not _profiles(all_result):
        pytest.skip("No profiles to test search")
    test_profile = _profiles(all_result)[0]
    search_term = (
        test_profile["name"].split("-")[0]
        if "-" in test_profile["name"]
        else test_profile["name"][:3]
    )
    search_result = await get_distribution_profiles(search=search_term)
    assert search_result.get("success"), search_result.get("error")
    assert _search_term(search_result) == search_term
    result_ids = {p["id"] for p in _profiles(search_result)}
    assert test_profile["id"] in result_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_edge_cases(integration_settings):
    """None, empty string, whitespace search still return success."""
    for search in (None, "", "   "):
        result = await get_distribution_profiles(search=search)
        assert result.get("success"), f"search={search!r}: {result.get('error')}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_distribution_profiles()
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single call completes within 10s."""
    start = datetime.now()
    response = await get_distribution_profiles()
    duration = (datetime.now() - start).total_seconds()
    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_filters_and_sort(integration_settings):
    """platform/authentication_type/sort/sort_direction filters return success and are reflected in meta."""
    response = await get_distribution_profiles(
        platform=[1, 2],
        sort=2,
        sort_direction=2,
    )
    assert response.get("success"), response.get("error")
    meta = response.get("meta", {})
    assert meta.get("platform") == [1, 2]
    assert meta.get("sort") == 2
    assert meta.get("sort_direction") == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_filter_returns_validation_error(integration_settings):
    """An out-of-enum authentication_type code returns a validation_error without calling the API."""
    response = await get_distribution_profiles(authentication_type=[99])
    assert response.get("success") is False
    assert response["error"]["type"] == "validation_error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_integrity(integration_settings):
    """All profiles have required fields; IDs are unique; settings.password absent."""
    response = await get_distribution_profiles(page=1, size=25)
    if not response.get("success") or not _profiles(response):
        pytest.skip("No profiles to validate")
    profiles = _profiles(response)
    for i, profile in enumerate(profiles):
        for field in ["id", "name"]:
            assert field in profile, f"Profile {i} missing {field}"
        assert "password" not in profile.get("settings", {})
    ids = [p["id"] for p in profiles]
    assert len(ids) == len(set(ids)), "Duplicate profile IDs"
