"""Unit tests for trigger_build: branch mode, commit mode, validation, and errors."""

import pytest
from httpx import Response

from src.tools.build_module.trigger_build import trigger_build

PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
WORKFLOW_ID = "aaaaaaaa-0002-0000-0000-000000000002"
COMMIT_ID = "aaaaaaaa-0003-0000-0000-000000000003"
CONFIG_ID = "aaaaaaaa-0004-0000-0000-000000000004"

SAMPLE_TRIGGER_RESPONSE = {
    "taskId": "aaaaaaaa-0005-0000-0000-000000000005",
    "queueItemId": "aaaaaaaa-0005-0000-0000-000000000005",
}


@pytest.mark.asyncio
async def test_trigger_build_branch_mode_success(mocked_api):
    """Branch mode PUTs to profiles/{id}/workflow/{id} with an empty body."""
    mocked_api.put(f"/build/v2/profiles/{PROFILE_ID}/workflow/{WORKFLOW_ID}").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID, branch_name="main")

    assert result["success"] is True
    assert result["data"] == SAMPLE_TRIGGER_RESPONSE
    assert result["meta"]["trigger_mode"] == "branch"
    assert result["meta"]["branch_name"] == "main"
    call = mocked_api.calls.last
    assert call.request.url.params["branchName"] == "main"
    assert call.request.content == b"{}"


@pytest.mark.asyncio
async def test_trigger_build_branch_mode_without_branch_name(mocked_api):
    """branch_name is optional; when omitted, no branchName param is sent."""
    mocked_api.put(f"/build/v2/profiles/{PROFILE_ID}/workflow/{WORKFLOW_ID}").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID)

    assert result["success"] is True
    assert "branchName" not in mocked_api.calls.last.request.url.params


@pytest.mark.asyncio
async def test_trigger_build_branch_mode_with_configuration_id(mocked_api):
    """configuration_id is passed as a configurationId query param in branch mode."""
    mocked_api.put(f"/build/v2/profiles/{PROFILE_ID}/workflow/{WORKFLOW_ID}").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID, configuration_id=CONFIG_ID)

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params["configurationId"] == CONFIG_ID


@pytest.mark.asyncio
async def test_trigger_build_branch_mode_missing_profile_id(mocked_api):
    """Missing profile_id in branch mode returns a validation_error without calling the API."""
    result = await trigger_build(workflow_id=WORKFLOW_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "trigger_build"
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_trigger_build_branch_mode_missing_workflow_id(mocked_api):
    """Missing workflow_id in branch mode returns a validation_error without calling the API."""
    result = await trigger_build(profile_id=PROFILE_ID)

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_trigger_build_commit_mode_default_workflow(mocked_api):
    """Commit mode without workflow_id POSTs to commits/{id}/build (last-used/default workflow)."""
    mocked_api.post(f"/build/v3/commits/{COMMIT_ID}/build").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(commit_id=COMMIT_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_TRIGGER_RESPONSE
    assert result["meta"]["trigger_mode"] == "commit"
    assert result["meta"]["commit_id"] == COMMIT_ID


@pytest.mark.asyncio
async def test_trigger_build_commit_mode_explicit_workflow(mocked_api):
    """Commit mode with workflow_id POSTs to commits/{id}/build/by-workflow."""
    mocked_api.post(f"/build/v3/commits/{COMMIT_ID}/build/by-workflow").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(commit_id=COMMIT_ID, workflow_id=WORKFLOW_ID, configuration_id=CONFIG_ID)

    assert result["success"] is True
    call = mocked_api.calls.last
    assert call.request.url.params["workflowId"] == WORKFLOW_ID
    assert call.request.url.params["configurationId"] == CONFIG_ID


@pytest.mark.asyncio
async def test_trigger_build_commit_mode_ignores_no_profile_requirement(mocked_api):
    """Commit mode does not require profile_id (unlike branch mode)."""
    mocked_api.post(f"/build/v3/commits/{COMMIT_ID}/build").mock(
        return_value=Response(202, json=SAMPLE_TRIGGER_RESPONSE)
    )

    result = await trigger_build(commit_id=COMMIT_ID)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_trigger_build_rejects_both_branch_name_and_commit_id(mocked_api):
    """Providing both branch_name and commit_id is a validation_error, no API call made."""
    result = await trigger_build(commit_id=COMMIT_ID, branch_name="main")

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_trigger_build_409_maps_to_invalid_state(mocked_api):
    """HTTP 409 (e.g. build already running) maps to type invalid_state, not http_error."""
    mocked_api.put(f"/build/v2/profiles/{PROFILE_ID}/workflow/{WORKFLOW_ID}").mock(
        return_value=Response(409, json={"message": "Build already in progress"})
    )

    result = await trigger_build(profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "trigger_build"
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 409


@pytest.mark.asyncio
async def test_trigger_build_422_maps_to_invalid_state(mocked_api):
    """HTTP 422 maps to type invalid_state."""
    mocked_api.post(f"/build/v3/commits/{COMMIT_ID}/build").mock(
        return_value=Response(422, json={"message": "Commit not buildable"})
    )

    result = await trigger_build(commit_id=COMMIT_ID)

    assert result["success"] is False
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 422


@pytest.mark.asyncio
async def test_trigger_build_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope (type http_error, not invalid_state)."""
    mocked_api.put(f"/build/v2/profiles/{PROFILE_ID}/workflow/{WORKFLOW_ID}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await trigger_build(profile_id=PROFILE_ID, workflow_id=WORKFLOW_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "trigger_build"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
