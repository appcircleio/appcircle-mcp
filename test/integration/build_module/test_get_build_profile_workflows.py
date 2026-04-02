"""
Integration tests for get_build_profile_workflows (real Appcircle API).

Run with: pytest test/integration/build/test_get_build_profile_workflows.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of workflows."""
    return response.get("data", [])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get one profile ID from list, then get workflows; success and data shape."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to fetch workflows for")
    profile_id = _profiles(list_result)[0]["id"]

    response = await get_build_profile_workflows(profile_id=profile_id)

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data_list(response)
    assert isinstance(data, list)
    assert "meta" in response
    assert response["meta"].get("count") == len(data)
    if data:
        for field in ["id", "profileId", "workflowName"]:
            assert field in data[0], f"Workflow missing field: {field}"
        assert data[0]["profileId"] == profile_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_build_profile_workflows(profile_id="any-uuid")
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_build_profile_workflows call completes within 10s."""
    list_result = await get_build_profiles(page=1, size=1)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to fetch workflows for")
    profile_id = _profiles(list_result)[0]["id"]

    start = datetime.now()
    response = await get_build_profile_workflows(profile_id=profile_id)
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile ID returns 404 and standard error envelope."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    result = await get_build_profile_workflows(profile_id=non_existent_id)

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_build_profile_workflows"
    assert result["error"].get("status_code") == 404
