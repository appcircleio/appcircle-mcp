"""
Integration tests for get_build_profile_details (real Appcircle API).

Run with: pytest test/integration/build/test_get_build_profile_details.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_build_profile_details import get_build_profile_details


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single profile for details."""
    return response.get("data", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get one profile ID from list, then get details; success and data shape."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_build_profile_details(profile_id=profile_id)

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert data.get("id") == profile_id
    for field in ["id", "name"]:
        assert field in data, f"Profile missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_excluded_fields(integration_settings):
    """No connectionEnvironmentKey or webhookSecret in details data."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to validate")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_build_profile_details(profile_id=profile_id)

    assert response.get("success"), response.get("error")
    data = _data(response)
    assert "connectionEnvironmentKey" not in data
    assert "webhookSecret" not in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_build_profile_details(profile_id="any-uuid")
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_build_profile_details call completes within 10s."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    start = datetime.now()
    response = await get_build_profile_details(profile_id=profile_id)
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile ID returns 404 and standard error envelope."""
    # Use a valid UUID format that is unlikely to exist
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    result = await get_build_profile_details(profile_id=non_existent_id)

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_build_profile_details"
    assert result["error"].get("status_code") == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_configurations_true(integration_settings):
    """When configurations=True, data includes configurations list from /build/v2/profiles/{id}/configurations."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to fetch details for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_build_profile_details(profile_id=profile_id, configurations=True)

    assert response.get("success"), response.get("error")
    data = _data(response)
    assert "configurations" in data
    assert isinstance(data["configurations"], list)
    assert data.get("id") == profile_id
