"""
Integration tests for update_app_version_release_notes (real Appcircle API, write/action).

WARNING: test_basic_functionality overwrites the release notes ("message") of a
real app version against the configured org. Run only against a dedicated test org.

Run with:
    APPCIRCLE_ACCESS_TOKEN=<test-org-token> APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true \\
        pytest test/integration/testing_distribution/test_update_app_version_release_notes.py -v -m integration_write
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.tools.testing_distribution.get_distribution_profile_details import get_distribution_profile_details
from src.tools.testing_distribution.get_distribution_profiles import get_distribution_profiles
from src.tools.testing_distribution.update_app_version_release_notes import update_app_version_release_notes


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    return response.get("data", {})


async def _find_app_version() -> Optional[Tuple[str, str, str]]:
    """Find a (profile_id, app_version_id, original_message) triple, or None."""
    list_result = await get_distribution_profiles(page=1, size=25)
    for profile in _profiles(list_result):
        profile_id = profile["id"]
        details = await get_distribution_profile_details(profile_id=profile_id, page=1, size=5)
        for app_version in _data(details).get("appVersions") or []:
            return profile_id, app_version["id"], app_version.get("message") or ""
    return None


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_basic_functionality(integration_write_settings):
    """Update a real app version's release notes, then restore the original message."""
    found = await _find_app_version()
    if not found:
        pytest.skip("No distribution app version found")
    profile_id, app_version_id, original_message = found

    response = await update_app_version_release_notes(
        profile_id=profile_id, app_version_id=app_version_id, message="Integration test release notes"
    )

    assert "success" in response
    if response.get("success"):
        assert response["data"].get("message") == "Integration test release notes"
        await update_app_version_release_notes(
            profile_id=profile_id, app_version_id=app_version_id, message=original_message
        )
    else:
        assert "error" in response
        assert response["error"].get("tool") == "update_app_version_release_notes"
        assert response["error"].get("type") in ("invalid_state", "http_error")


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_write_settings):
    """Non-existent profile/app version returns an error envelope."""
    result = await update_app_version_release_notes(
        profile_id="00000000-0000-0000-0000-000000000000",
        app_version_id="00000000-0000-0000-0000-000000000000",
        message="test",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "update_app_version_release_notes"
