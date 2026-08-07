"""
Integration tests for get_publish_metadata_lock_status (real Appcircle API).

Run with: pytest test/integration/publish_to_stores/test_get_publish_metadata_lock_status.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from typing import Any, Dict, List

import pytest

from src.tools.publish_to_stores.get_publish_metadata_lock_status import (
    get_publish_metadata_lock_status,
)
from src.tools.publish_to_stores.get_publish_profiles import get_publish_profiles


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get one publish profile ID, then fetch its metadata lock status."""
    list_result = await get_publish_profiles(platform_type="ios", page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No iOS publish profiles to check lock status for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_publish_metadata_lock_status(platform_type="ios", profile_id=profile_id)

    assert response.get("success"), response.get("error")
    assert "data" in response
    assert isinstance(response["data"].get("locked"), bool)
    assert response["meta"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile returns an error envelope (likely 404)."""
    result = await get_publish_metadata_lock_status(
        platform_type="ios",
        profile_id="00000000-0000-0000-0000-000000000000",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_publish_metadata_lock_status"
