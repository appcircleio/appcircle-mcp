"""
Integration tests for get_publish_details (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/test_get_publish_details.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.tools.publish_to_stores.get_publish_details import get_publish_details
from src.tools.publish_to_stores.get_publish_profile_details import get_publish_profile_details
from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    return response.get("data", {})


async def _find_profile_and_app_version(platform_type: str) -> Optional[Tuple[str, str]]:
    """Find a (profile_id, app_version_id) pair with at least one app version, or None."""
    list_result = await get_publish_profiles(platform_type=platform_type, page=1, size=25)
    for profile in _profiles(list_result):
        details = await get_publish_profile_details(
            platform_type=platform_type, profile_id=profile["id"], page=1, size=1
        )
        app_versions = _data(details).get("appVersions") or []
        if app_versions:
            return profile["id"], app_versions[0]["id"]
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Discover a real profile/app version, fetch its publish details; success or valid not-found error."""
    found = await _find_profile_and_app_version("ios") or await _find_profile_and_app_version("android")
    if not found:
        pytest.skip("No publish profile with at least one app version found")
    profile_id, app_version_id = found

    response = await get_publish_details(
        platform_type="ios", profile_id=profile_id, app_version_id=app_version_id
    )

    assert "success" in response
    if response.get("success"):
        data = response.get("data", {})
        assert isinstance(data, dict)
        assert response["meta"] == {}
        if "steps" in data:
            assert isinstance(data["steps"], list)
    else:
        assert "error" in response
        assert response["error"].get("tool") == "get_publish_details"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent app version returns an error envelope (likely 404)."""
    result = await get_publish_details(
        platform_type="ios",
        profile_id="00000000-0000-0000-0000-000000000000",
        app_version_id="00000000-0000-0000-0000-000000000000",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_publish_details"
