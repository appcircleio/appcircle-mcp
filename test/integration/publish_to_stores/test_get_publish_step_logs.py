"""
Integration tests for get_publish_step_logs (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/test_get_publish_step_logs.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.tools.publish_to_stores.get_publish_details import get_publish_details
from src.tools.publish_to_stores.get_publish_profile_details import get_publish_profile_details
from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles
from src.tools.publish_to_stores.get_publish_step_logs import get_publish_step_logs


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    return response.get("data", {})


async def _find_publish_and_step(platform_type: str) -> Optional[Tuple[str, str, str]]:
    """Find a (profile_id, publish_id, step_id) triple with at least one publish step, or None."""
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
            steps = publish_data.get("steps") or []
            if publish_data.get("id") and steps:
                return profile_id, publish_data["id"], steps[0]["id"]
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Discover a real publish run/step, fetch its logs; success and data shape."""
    found = await _find_publish_and_step("ios") or await _find_publish_and_step("android")
    if not found:
        pytest.skip("No publish flow run with at least one step found")
    profile_id, publish_id, step_id = found

    response = await get_publish_step_logs(
        platform_type="ios", profile_id=profile_id, publish_id=publish_id, step_id=step_id
    )

    assert "success" in response
    if response.get("success"):
        assert isinstance(response["data"], str)
        meta = response["meta"]
        for field in ["total_lines", "returned_lines", "truncated", "full_log", "step", "steps"]:
            assert field in meta
    else:
        assert "error" in response
        assert response["error"].get("tool") == "get_publish_step_logs"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent publish/step returns an error envelope (likely 404)."""
    result = await get_publish_step_logs(
        platform_type="ios",
        profile_id="00000000-0000-0000-0000-000000000000",
        publish_id="00000000-0000-0000-0000-000000000000",
        step_id="00000000-0000-0000-0000-000000000000",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_publish_step_logs"
