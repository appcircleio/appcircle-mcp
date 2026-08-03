"""
Integration tests for trigger_build (real Appcircle API, write/action).

WARNING: test_basic_functionality actually triggers a real build against the
configured org, consuming build minutes. Run only against a dedicated test org.

Run with:
    APPCIRCLE_ACCESS_TOKEN=<test-org-token> APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true \\
        pytest test/integration/build_module/test_trigger_build.py -v -m integration_write
"""

from typing import Any, Dict, List

import pytest

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows
from src.tools.build_module.trigger_build import trigger_build


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_basic_functionality(integration_write_settings):
    """Discover a real profile/workflow, trigger a build; success or a valid invalid_state error."""
    list_result = await get_build_profiles(page=1, size=5)
    if not list_result.get("success") or not _profiles(list_result):
        pytest.skip("No build profiles to trigger a build for")

    profile_id = None
    workflow_id = None
    for profile in _profiles(list_result):
        workflows_result = await get_build_profile_workflows(profile_id=profile["id"])
        workflows = workflows_result.get("data", []) if workflows_result.get("success") else []
        if workflows:
            profile_id = profile["id"]
            workflow_id = workflows[0]["id"]
            break

    if not profile_id or not workflow_id:
        pytest.skip("No profile with at least one workflow found")

    response = await trigger_build(profile_id=profile_id, workflow_id=workflow_id)

    assert "success" in response
    if response.get("success"):
        assert "taskId" in response["data"]
        assert "queueItemId" in response["data"]
        assert response["meta"]["trigger_mode"] == "branch"
    else:
        assert "error" in response
        assert response["error"].get("tool") == "trigger_build"
        assert response["error"].get("type") in ("invalid_state", "http_error")


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_validation_error_does_not_call_api(integration_write_settings):
    """Missing required args returns validation_error without hitting the real API."""
    result = await trigger_build()

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
