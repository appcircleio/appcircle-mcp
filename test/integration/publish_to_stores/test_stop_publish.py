"""
Integration tests for stop_publish (real Appcircle API, write/action).

WARNING: test_basic_functionality starts and then cancels a real publish flow
run against the configured org. Run only against a dedicated test org.

Run with:
    APPCIRCLE_ACCESS_TOKEN=<test-org-token> APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true \\
        pytest test/integration/publish_to_stores/test_stop_publish.py -v -m integration_write
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.tools.publish_to_stores.get_publish_details import get_publish_details
from src.tools.publish_to_stores.get_publish_profile_details import get_publish_profile_details
from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles
from src.tools.publish_to_stores.start_publish import start_publish
from src.tools.publish_to_stores.stop_publish import stop_publish


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    return response.get("data", {})


async def _find_publish_id(platform_type: str) -> Optional[Tuple[str, str]]:
    """Find a (profile_id, publish_id) pair with a resolvable publish flow, or None."""
    list_result = await get_publish_profiles(platform_type=platform_type, page=1, size=25)
    for profile in _profiles(list_result):
        profile_id = profile["id"]
        details = await get_publish_profile_details(
            platform_type=platform_type, profile_id=profile_id, page=1, size=5
        )
        for app_version in _data(details).get("appVersions") or []:
            publish_details = await get_publish_details(
                platform_type=platform_type, profile_id=profile_id, app_version_id=app_version["id"]
            )
            publish_data = _data(publish_details)
            if publish_data.get("id"):
                return profile_id, publish_data["id"]
    return None


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_basic_functionality(integration_write_settings):
    """Start a real publish flow run, then stop it; success or a valid invalid_state error."""
    found = await _find_publish_id("ios") or await _find_publish_id("android")
    if not found:
        pytest.skip("No publish flow run found")
    profile_id, publish_id = found

    start_response = await start_publish(platform_type="ios", profile_id=profile_id, publish_id=publish_id)
    if not start_response.get("success"):
        pytest.skip(f"Could not start a publish run to cancel: {start_response.get('error')}")

    response = await stop_publish(platform_type="ios", profile_id=profile_id, publish_id=publish_id)

    assert "success" in response
    if response.get("success"):
        assert "task_id" in response["data"]
    else:
        assert "error" in response
        assert response["error"].get("tool") == "stop_publish"
        assert response["error"].get("type") in ("invalid_state", "http_error")


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_write_settings):
    """Non-existent profile/publish returns an error envelope."""
    result = await stop_publish(
        platform_type="ios",
        profile_id="00000000-0000-0000-0000-000000000000",
        publish_id="00000000-0000-0000-0000-000000000000",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "stop_publish"
