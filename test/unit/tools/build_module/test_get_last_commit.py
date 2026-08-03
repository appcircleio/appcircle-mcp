"""Unit tests for get_last_commit: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_last_commit import get_last_commit

# Mock IDs for tests (no real org/profile/branch or author data)
BRANCH_ID = "aaaaaaaa-0001-0000-0000-000000000001"

SAMPLE_LAST_COMMIT = {
    "id": "aaaaaaaa-0002-0000-0000-000000000002",
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "profileId": "aaaaaaaa-0003-0000-0000-000000000003",
    "branchId": BRANCH_ID,
    "hash": "deadbeef00000000000000000000000000000002",
    "message": "Production Release",
    "author": "author",
    "eMail": "author@example.com",
    "commitDate": "2026-01-14T15:14:17+00:00",
    "tags": None,
    "targetBranchId": None,
    "targetHash": None,
    "pullNumber": None,
}


@pytest.mark.asyncio
async def test_get_last_commit_success(mocked_api):
    """Returns success envelope with data when API returns the last commit (unwrapped)."""
    mocked_api.get("/build/v2/commits/last-commit").mock(
        return_value=Response(200, json=SAMPLE_LAST_COMMIT)
    )

    result = await get_last_commit(branch_id=BRANCH_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LAST_COMMIT
    assert result["meta"] == {}
    params = mocked_api.calls.last.request.url.params
    assert params.get("branchId") == BRANCH_ID


@pytest.mark.asyncio
async def test_get_last_commit_wrapper_response(mocked_api):
    """API returning a { data: ... } wrapper is normalized; data contains the commit object."""
    mocked_api.get("/build/v2/commits/last-commit").mock(
        return_value=Response(200, json={"data": SAMPLE_LAST_COMMIT})
    )

    result = await get_last_commit(branch_id=BRANCH_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LAST_COMMIT


@pytest.mark.asyncio
async def test_get_last_commit_not_found_returns_unified_envelope(mocked_api):
    """When API returns 404 (e.g. branch has no commits), tool returns standard error envelope."""
    mocked_api.get("/build/v2/commits/last-commit").mock(
        return_value=Response(404, json={"message": "Not found"})
    )

    result = await get_last_commit(branch_id=BRANCH_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_last_commit"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_get_last_commit_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/build/v2/commits/last-commit").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_last_commit(branch_id=BRANCH_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_last_commit"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
