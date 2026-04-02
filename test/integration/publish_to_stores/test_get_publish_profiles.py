"""
Integration tests for get_publish_profiles (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/ -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _count(response: Dict[str, Any]) -> int:
    """Unified envelope: count is in meta."""
    return response.get("meta", {}).get("count", 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_ios(integration_settings):
    """Returns success with data and meta for platform_type=ios."""
    response = await get_publish_profiles(platform_type="ios")
    assert response.get("success"), response.get("error")
    assert "data" in response
    assert "meta" in response
    assert response["meta"].get("platform_type") == "ios"
    profiles = _profiles(response)
    assert isinstance(profiles, list)
    assert _count(response) == len(profiles)
    if profiles:
        for field in ["id", "name"]:
            assert field in profiles[0], f"Profile missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_android(integration_settings):
    """Returns success with data and meta for platform_type=android."""
    response = await get_publish_profiles(platform_type="android")
    assert response.get("success"), response.get("error")
    assert "data" in response
    assert "meta" in response
    assert response["meta"].get("platform_type") == "android"
    assert isinstance(_profiles(response), list)
    assert _count(response) == len(_profiles(response))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination(integration_settings):
    """Pagination params return a page; meta has page, page_size, count."""
    response = await get_publish_profiles(platform_type="ios", page=1, size=5)
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
async def test_flow_status_filter(integration_settings):
    """flow_status is passed and reflected in meta."""
    response = await get_publish_profiles(platform_type="ios", flow_status=0)
    assert response.get("success"), response.get("error")
    assert response.get("meta", {}).get("flow_status") == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """On API error, returns standard error envelope."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_publish_profiles(platform_type="ios")
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = os.getenv("APPCIRCLE_ACCESS_TOKEN") or original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single call completes within 10s."""
    start = datetime.now()
    response = await get_publish_profiles(platform_type="ios")
    duration = (datetime.now() - start).total_seconds()
    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"
