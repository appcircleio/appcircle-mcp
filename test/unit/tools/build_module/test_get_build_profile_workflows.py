"""Unit tests for get_build_profile_workflows: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_build_profile_workflows import get_build_profile_workflows

# Mock IDs for tests (no real org/profile/workflow data)
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"

SAMPLE_WORKFLOWS = [
    {
        "id": "aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "profileId": PROFILE_ID,
        "workflowName": "Default Push Workflow",
        "lastUsedTime": "2025-11-05T10:40:39.4444847+00:00",
    },
    {
        "id": "aaaaaaaa-0003-0000-0000-000000000003",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "profileId": PROFILE_ID,
        "workflowName": "Default PR Workflow",
        "lastUsedTime": "2025-10-16T13:26:39.8550034+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_build_profile_workflows_success(mocked_api):
    """Returns success envelope with data (list of workflows) and meta count when API returns list."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows").mock(
        return_value=Response(200, json=SAMPLE_WORKFLOWS)
    )

    result = await get_build_profile_workflows(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_WORKFLOWS
    assert len(result["data"]) == 2
    assert result["data"][0]["profileId"] == PROFILE_ID
    assert result["data"][0]["workflowName"] == "Default Push Workflow"
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.path == f"/build/v2/profiles/{PROFILE_ID}/workflows"


@pytest.mark.asyncio
async def test_get_build_profile_workflows_empty_list(mocked_api):
    """Returns success with empty data list and count 0 when API returns empty list."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows").mock(
        return_value=Response(200, json=[])
    )

    result = await get_build_profile_workflows(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_build_profile_workflows_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data/workflows) is normalized to list in data."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows").mock(
        return_value=Response(200, json={"data": SAMPLE_WORKFLOWS})
    )

    result = await get_build_profile_workflows(profile_id=PROFILE_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_WORKFLOWS
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_get_build_profile_workflows_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/build/v2/profiles/{PROFILE_ID}/workflows").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_build_profile_workflows(profile_id=PROFILE_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_build_profile_workflows"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
