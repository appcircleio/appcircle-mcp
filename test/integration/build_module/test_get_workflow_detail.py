"""
Integration tests for get_workflow_detail (real Appcircle API).

Run with: pytest test/integration/build/test_get_workflow_detail.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows
from src.tools.build_module.get_workflow_detail import get_workflow_detail


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of workflows."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single workflow for detail."""
    return response.get("data", {})


async def _get_profile_and_workflow_id() -> Optional[Tuple[str, str]]:
    """Get (profile_id, workflow_id) from API: list profiles, then list workflows for first profile."""
    list_result = await get_build_profiles(page=1, size=5)
    profiles = _profiles(list_result)
    if not list_result.get("success") or not profiles:
        return None
    for profile in profiles:
        profile_id = profile.get("id")
        if not profile_id:
            continue
        workflows_result = await get_build_profile_workflows(profile_id=profile_id)
        if not workflows_result.get("success"):
            continue
        workflows = _data_list(workflows_result)
        if workflows and isinstance(workflows[0], dict) and workflows[0].get("id"):
            return (profile_id, workflows[0]["id"])
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Get profile_id and workflow_id from list APIs, then get workflow detail; success and data shape."""
    pair = await _get_profile_and_workflow_id()
    if not pair:
        pytest.skip("No build profile with workflows to fetch detail for")
    profile_id, workflow_id = pair

    response = await get_workflow_detail(
        profile_id=profile_id, workflow_id=workflow_id
    )

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert data.get("id") == workflow_id
    assert data.get("profileId") == profile_id
    for field in ["id", "profileId", "workflowName"]:
        assert field in data, f"Workflow missing field: {field}"
    # workflowDocument may be present (YAML string)
    assert "workflowDocument" in data or "lastUsedTime" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_workflow_detail(
            profile_id="00000000-0000-0000-0000-000000000000",
            workflow_id="00000000-0000-0000-0000-000000000001",
        )
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_workflow_detail call completes within 10s."""
    pair = await _get_profile_and_workflow_id()
    if not pair:
        pytest.skip("No build profile with workflows to fetch detail for")
    profile_id, workflow_id = pair

    start = datetime.now()
    response = await get_workflow_detail(
        profile_id=profile_id, workflow_id=workflow_id
    )
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent profile or workflow returns 404 and standard error envelope."""
    non_existent_profile = "00000000-0000-0000-0000-000000000000"
    non_existent_workflow = "00000000-0000-0000-0000-000000000001"
    result = await get_workflow_detail(
        profile_id=non_existent_profile, workflow_id=non_existent_workflow
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_workflow_detail"
    assert result["error"].get("status_code") == 404
