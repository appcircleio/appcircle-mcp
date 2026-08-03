"""
Integration tests for cancel_build (real Appcircle API, write/action).

WARNING: test_basic_functionality actually triggers and then cancels a real
build against the configured org. Run only against a dedicated test org.

Run with:
    APPCIRCLE_ACCESS_TOKEN=<test-org-token> APPCIRCLE_RUN_WRITE_INTEGRATION_TESTS=true \\
        pytest test/integration/build_module/test_cancel_build.py -v -m integration_write
"""

from typing import Any, Dict, List

import pytest

from src.tools.build_module.cancel_build import cancel_build
from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows
from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.trigger_build import trigger_build


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    return response.get("data", [])


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_basic_functionality(integration_write_settings):
    """Trigger a real build, then cancel it; success or a valid invalid_state error."""
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

    trigger_response = await trigger_build(profile_id=profile_id, workflow_id=workflow_id)
    if not trigger_response.get("success"):
        pytest.skip(f"Could not trigger a build to cancel: {trigger_response.get('error')}")
    task_id = trigger_response["data"]["taskId"]

    response = await cancel_build(task_id=task_id)

    assert "success" in response
    if response.get("success"):
        assert response["data"] == {"task_id": task_id, "cancelled": True}
    else:
        assert "error" in response
        assert response["error"].get("tool") == "cancel_build"
        assert response["error"].get("type") in ("invalid_state", "http_error")


@pytest.mark.integration_write
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_write_settings):
    """Cancelling a non-existent task_id returns an error envelope."""
    result = await cancel_build(task_id="00000000-0000-0000-0000-000000000000")

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "cancel_build"
