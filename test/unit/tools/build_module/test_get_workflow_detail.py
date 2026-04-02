"""Unit tests for get_workflow_detail: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_workflow_detail import get_workflow_detail

# Mock IDs for tests (no real org/profile/workflow data)
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
WORKFLOW_ID = "aaaaaaaa-0002-0000-0000-000000000002"

SAMPLE_WORKFLOW = {
    "id": WORKFLOW_ID,
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "profileId": PROFILE_ID,
    "workflowName": "Default Push Workflow",
    "workflowDocument": "directories:\n  - AC_SOURCE\nsteps:\n  - componentType: appcircle_git_clone\n",
    "lastUsedTime": "2025-11-05T10:40:39.4444847+00:00",
}


@pytest.mark.asyncio
async def test_get_workflow_detail_success(mocked_api):
    """Returns success envelope with data when API returns a workflow."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows/{WORKFLOW_ID}").mock(
        return_value=Response(200, json=SAMPLE_WORKFLOW)
    )

    result = await get_workflow_detail(
        profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID
    )

    assert result["success"] is True
    assert result["data"]["id"] == WORKFLOW_ID
    assert result["data"]["profileId"] == PROFILE_ID
    assert result["data"]["workflowName"] == "Default Push Workflow"
    assert "workflowDocument" in result["data"]
    assert result["meta"] == {}
    assert (
        mocked_api.calls.last.request.url.path
        == f"/build/v2/profiles/{PROFILE_ID}/workflows/{WORKFLOW_ID}"
    )


@pytest.mark.asyncio
async def test_get_workflow_detail_response_passthrough(mocked_api):
    """Full API response is returned in data without modification when raw object."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows/{WORKFLOW_ID}").mock(
        return_value=Response(200, json=SAMPLE_WORKFLOW)
    )

    result = await get_workflow_detail(
        profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_WORKFLOW


@pytest.mark.asyncio
async def test_get_workflow_detail_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data) is normalized; data contains workflow object."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows/{WORKFLOW_ID}").mock(
        return_value=Response(200, json={"data": SAMPLE_WORKFLOW})
    )

    result = await get_workflow_detail(
        profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID
    )

    assert result["success"] is True
    assert result["data"] == SAMPLE_WORKFLOW


@pytest.mark.asyncio
async def test_get_workflow_detail_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows/{WORKFLOW_ID}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_workflow_detail(
        profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID
    )

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_workflow_detail"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
