"""Unit tests for get_commit_details: success, validation, and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_commit_details import get_commit_details

# Mock IDs and hashes for tests (no real org/commit/author data)
COMMIT_ID = "aaaaaaaa-0001-0000-0000-000000000001"
COMMIT_HASH = "deadbeef00000000000000000000000000000000"

SAMPLE_COMMIT_BY_ID = {
    "id": COMMIT_ID,
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "profileId": "aaaaaaaa-0002-0000-0000-000000000002",
    "branchId": "aaaaaaaa-0003-0000-0000-000000000003",
    "hash": COMMIT_HASH,
    "message": "Change display name",
    "author": "author@example.com",
    "email": "author@example.com",
    "commitDate": "2025-12-25T11:55:46+00:00",
    "tags": None,
    "builds": [],
    "targetBranchId": None,
    "targetHash": None,
    "pullNumber": None,
    "deletedOnRepo": False,
    "commitStatus": 0,
    "description": "",
}

# Mock commit hash (40 hex chars) for by-hash lookup tests
MOCK_COMMIT_HASH = "deadbeef00000000000000000000000000000001"

SAMPLE_COMMIT_BY_HASH = {
    "id": "aaaaaaaa-0004-0000-0000-000000000004",
    "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "profileId": "aaaaaaaa-0005-0000-0000-000000000005",
    "branchId": "aaaaaaaa-0006-0000-0000-000000000006",
    "hash": MOCK_COMMIT_HASH,
    "message": "Production Release",
    "author": "testuser",
    "email": "test@example.com",
    "commitDate": "2026-01-14T15:14:17+00:00",
    "tags": None,
    "builds": [],
    "targetBranchId": None,
    "targetHash": None,
    "pullNumber": None,
    "deletedOnRepo": False,
    "commitStatus": 0,
    "description": "",
}


@pytest.mark.asyncio
async def test_get_commit_details_by_id_success(mocked_api):
    """Returns success envelope with data when API returns commit by commit_id."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}").mock(
        return_value=Response(200, json=SAMPLE_COMMIT_BY_ID)
    )

    result = await get_commit_details(commit_id=COMMIT_ID)

    assert result["success"] is True
    assert result["data"]["id"] == COMMIT_ID
    assert result["data"]["hash"] == COMMIT_HASH
    assert result["data"]["message"] == "Change display name"
    assert result["meta"] == {}
    assert mocked_api.calls.last.request.url.path == f"/build/v2/commits/{COMMIT_ID}"


@pytest.mark.asyncio
async def test_get_commit_details_by_hash_success(mocked_api):
    """Returns success envelope with data when API returns commit by commit_hash."""
    hash_for_url = MOCK_COMMIT_HASH
    mocked_api.get(f"/build/v2/commits/{hash_for_url}").mock(
        return_value=Response(200, json=SAMPLE_COMMIT_BY_HASH)
    )

    result = await get_commit_details(commit_hash=hash_for_url)

    assert result["success"] is True
    assert result["data"]["hash"] == hash_for_url
    assert result["data"]["message"] == "Production Release"
    assert result["meta"] == {}
    assert mocked_api.calls.last.request.url.path == f"/build/v2/commits/{hash_for_url}"


@pytest.mark.asyncio
async def test_get_commit_details_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data) is normalized; data contains commit object."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}").mock(
        return_value=Response(200, json={"data": SAMPLE_COMMIT_BY_ID})
    )

    result = await get_commit_details(commit_id=COMMIT_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_COMMIT_BY_ID


@pytest.mark.asyncio
async def test_get_commit_details_both_params_validation_error(mocked_api):
    """When both commit_id and commit_hash are provided, returns validation_error envelope."""
    result = await get_commit_details(commit_id=COMMIT_ID, commit_hash=COMMIT_HASH)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_commit_details"
    assert result["error"]["type"] == "validation_error"
    assert "not both" in result["error"]["message"]
    assert mocked_api.calls.call_count == 0


@pytest.mark.asyncio
async def test_get_commit_details_neither_param_validation_error(mocked_api):
    """When neither commit_id nor commit_hash is provided, returns validation_error envelope."""
    result = await get_commit_details()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_commit_details"
    assert result["error"]["type"] == "validation_error"
    assert "Provide either" in result["error"]["message"]
    assert mocked_api.calls.call_count == 0


@pytest.mark.asyncio
async def test_get_commit_details_empty_string_validation_error(mocked_api):
    """When both are empty string, treated as neither provided."""
    result = await get_commit_details(commit_id="", commit_hash="")

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert mocked_api.calls.call_count == 0


@pytest.mark.asyncio
async def test_get_commit_details_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get(f"/build/v2/commits/{COMMIT_ID}").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_commit_details(commit_id=COMMIT_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_commit_details"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
