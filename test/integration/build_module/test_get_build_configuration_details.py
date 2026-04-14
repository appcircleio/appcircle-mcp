"""
Integration tests for get_build_configuration_details (real Appcircle API).

Run with: pytest test/integration/build/test_get_build_configuration_details.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_build_profile_details import get_build_profile_details
from src.tools.build_module.get_build_configuration_details import get_build_configuration_details


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single object for details."""
    return response.get("data", {})


async def _get_profile_and_configuration_id() -> Optional[Tuple[str, str]]:
    """Get (profile_id, configuration_id) by listing profiles and fetching details with configurations=True."""
    list_result = await get_build_profiles(page=1, size=10)
    profiles = _profiles(list_result)
    if not list_result.get("success") or not profiles:
        return None
    for profile in profiles:
        profile_id = profile.get("id")
        if not profile_id:
            continue
        details_result = await get_build_profile_details(
            profile_id=profile_id, configurations=True
        )
        if not details_result.get("success"):
            continue
        profile_data = _data(details_result)
        configs = profile_data.get("configurations")
        if isinstance(configs, list) and configs:
            first = configs[0]
            configuration_id = None
            if isinstance(first, dict):
                # API list returns items as { "item1": { config with "id" }, "item2": {} }
                item1 = first.get("item1") if isinstance(first.get("item1"), dict) else None
                if item1 and item1.get("id"):
                    configuration_id = item1["id"]
                elif first.get("id"):
                    configuration_id = first["id"]
            if configuration_id:
                return (profile_id, configuration_id)
            if isinstance(first, str):
                return (profile_id, first)
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get build configuration details; success and data shape (item1/item2)."""
    pair = await _get_profile_and_configuration_id()
    if not pair:
        pytest.skip(
            "No build profile with configuration found (list profiles and profile details to get configuration id)"
        )
    profile_id, configuration_id = pair

    response = await get_build_configuration_details(
        profile_id=profile_id, configuration_id=configuration_id
    )

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert "item1" in data, "Expected API to return item1 (configuration object)"
    item1 = data["item1"]
    assert isinstance(item1, dict)
    assert item1.get("id") == configuration_id
    assert item1.get("profileId") == profile_id
    for field in ["id", "profileId", "configurationName", "platformType"]:
        assert field in item1, f"item1 missing field: {field}"
    if "item2" in data:
        assert isinstance(data["item2"], dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_build_configuration_details(
            profile_id="00000000-0000-0000-0000-000000000000",
            configuration_id="00000000-0000-0000-0000-000000000001",
        )
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile or configuration returns 404 and standard error envelope."""
    non_existent_profile = "00000000-0000-0000-0000-000000000000"
    non_existent_config = "00000000-0000-0000-0000-000000000001"
    result = await get_build_configuration_details(
        profile_id=non_existent_profile, configuration_id=non_existent_config
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_build_configuration_details"
    assert result["error"].get("status_code") == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_build_configuration_details call completes within 10s."""
    pair = await _get_profile_and_configuration_id()
    if not pair:
        pytest.skip("No build profile with configuration found")
    profile_id, configuration_id = pair

    start = datetime.now()
    response = await get_build_configuration_details(
        profile_id=profile_id, configuration_id=configuration_id
    )
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"
