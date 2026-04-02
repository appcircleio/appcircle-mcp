"""
Integration tests for get_publish_profile_details (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/test_get_publish_profile_details.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles
from src.tools.publish_to_stores.get_publish_profile_details import get_publish_profile_details


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single profile for details."""
    return response.get("data", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_ios(integration_settings):
    """Get one iOS profile ID from list, then get details; success and data shape."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_profile_details(platform_type="ios", profile_id=profile_id)

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert data.get("id") == profile_id
    for field in ["id", "name"]:
        assert field in data, f"Profile missing field: {field}"
    assert "appVersions" in data
    assert isinstance(data.get("appVersions"), list)
    assert response.get("meta", {}).get("platform_type") == "ios"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_android(integration_settings):
    """Get one Android profile ID from list, then get details."""
    list_result = await get_publish_profiles(platform_type="android", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No Android publish profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_profile_details(platform_type="android", profile_id=profile_id)

    assert response.get("success"), response.get("error")
    data = _data(response)
    assert data.get("id") == profile_id
    assert response.get("meta", {}).get("platform_type") == "android"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagination(integration_settings):
    """App versions pagination: page and size in request; meta has page, page_size."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_profile_details(
        platform_type="ios", profile_id=profile_id, page=1, size=2
    )

    assert response.get("success"), response.get("error")
    data = _data(response)
    meta = response.get("meta", {})
    assert "page" in meta
    assert "page_size" in meta
    assert len(data.get("appVersions", [])) <= 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_excluded_fields(integration_settings):
    """No signedCertThumbPrint in profile or in app versions."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to validate")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_profile_details(platform_type="ios", profile_id=profile_id)

    assert response.get("success"), response.get("error")
    data = _data(response)
    assert "signedCertThumbPrint" not in data
    for av in data.get("appVersions", []):
        assert "signedCertThumbPrint" not in av


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_publish_profile_details(
            platform_type="ios", profile_id="any-uuid"
        )
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_publish_profile_details call completes within 10s."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    start = datetime.now()
    response = await get_publish_profile_details(platform_type="ios", profile_id=profile_id)
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile ID returns 404 and standard error envelope."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    result = await get_publish_profile_details(
        platform_type="ios", profile_id=non_existent_id
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_publish_profile_details"
    assert result["error"].get("status_code") == 404
