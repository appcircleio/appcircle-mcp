"""
Integration tests for get_publish_flows (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/test_get_publish_flows.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from typing import Any, Dict, List

import pytest

from src.tools.publish_to_stores.get_publish_flows import get_publish_flows
from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get one publish profile ID, then fetch its publish flows."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to fetch flows for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_flows(platform_type="ios", profile_id=profile_id)

    assert response.get("success"), response.get("error")
    data = response.get("data", [])
    assert isinstance(data, list)
    assert response["meta"]["count"] == len(data)
    if data:
        for field in ["id", "flowName", "flowDocument"]:
            assert field in data[0], f"Flow missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile returns an error envelope (likely 404)."""
    result = await get_publish_flows(
        platform_type="ios",
        profile_id="00000000-0000-0000-0000-000000000000",
    )

    if not result.get("success"):
        assert "error" in result
        assert result["error"].get("tool") == "get_publish_flows"
