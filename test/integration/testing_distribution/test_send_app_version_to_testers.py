"""
Integration tests for send_app_version_to_testers (real Appcircle API, write/action).

WARNING: test_basic_functionality sends a real notification to a real tester/testing
group for a real app version against the configured org. Run only against a
dedicated test org, with a tester/group you control.

Run with:
    APPCIRCLE_ACCESS_TOKEN=<test-org-token> APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true \\
        pytest test/integration/testing_distribution/test_send_app_version_to_testers.py -v -m integration_write
"""

import os
from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.tools.testing_distribution.get_distribution_profile_details import get_distribution_profile_details
from src.tools.testing_distribution.get_distribution_profiles import get_distribution_profiles
from src.tools.testing_distribution.get_testing_groups import get_testing_groups
from src.tools.testing_distribution.send_app_version_to_testers import send_app_version_to_testers


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    return response.get("data", {})


async def _find_app_version() -> Optional[Tuple[str, str]]:
    """Find a (profile_id, app_version_id) pair, or None."""
    list_result = await get_distribution_profiles(page=1, size=25)
    for profile in _profiles(list_result):
        profile_id = profile["id"]
        details = await get_distribution_profile_details(profile_id=profile_id, page=1, size=5)
        for app_version in _data(details).get("appVersions") or []:
            return profile_id, app_version["id"]
    return None


async def _find_testing_group_id() -> Optional[str]:
    """Find a real testing group ID to send to, or None."""
    result = await get_testing_groups()
    groups = result.get("data", [])
    return groups[0]["id"] if groups else None


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_basic_functionality(integration_write_settings):
    """Send a real app version to a real testing group; success or a valid invalid_state error."""
    found = await _find_app_version()
    if not found:
        pytest.skip("No distribution app version found")
    profile_id, app_version_id = found

    group_id = await _find_testing_group_id()
    if not group_id:
        pytest.skip("No testing group found to send to")

    response = await send_app_version_to_testers(
        profile_id=profile_id,
        app_version_id=app_version_id,
        message="Integration test notification",
        testers=[group_id],
    )

    assert "success" in response
    if response.get("success"):
        assert "taskId" in response["data"]
    else:
        assert "error" in response
        assert response["error"].get("tool") == "send_app_version_to_testers"
        assert response["error"].get("type") in ("invalid_state", "http_error")


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_write_settings):
    """Non-existent profile/app version returns an error envelope."""
    result = await send_app_version_to_testers(
        profile_id="00000000-0000-0000-0000-000000000000",
        app_version_id="00000000-0000-0000-0000-000000000000",
        message="test",
        testers=["test@example.com"],
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "send_app_version_to_testers"
