"""Unit tests for get_commits_by_branch: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_commits_by_branch import get_commits_by_branch

# Mock IDs for tests (no real org/profile/branch or author data)
BRANCH_ID = "aaaaaaaa-0001-0000-0000-000000000001"

SAMPLE_COMMITS = [
    {
        "id": "aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "profileId": "aaaaaaaa-0003-0000-0000-000000000003",
        "branchId": BRANCH_ID,
        "hash": "deadbeef00000000000000000000000000000002",
        "message": "Create README.md",
        "author": "author@example.com",
        "email": "author@example.com",
        "commitDate": "2025-07-21T07:27:26+00:00",
        "tags": ["test-tag", "test"],
        "builds": [],
        "targetBranchId": None,
        "targetHash": None,
        "pullNumber": None,
        "deletedOnRepo": False,
        "commitStatus": 0,
        "description": "",
    },
]

SAMPLE_PAGINATION = {
    "page": 1,
    "perPage": 25,
    "pageCount": 1,
    "totalCount": 19,
    "enablePrevious": False,
    "enableNext": False,
}


@pytest.mark.asyncio
async def test_get_commits_by_branch_success_no_pagination(mocked_api):
    """Returns success envelope with data and count in meta when no page/size (raw list)."""
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json=SAMPLE_COMMITS)
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_COMMITS
    assert result["meta"]["count"] == 1
    params = mocked_api.calls.last.request.url.params
    assert params.get("branchId") == BRANCH_ID
    assert params.get("page") is None
    assert params.get("size") is None


@pytest.mark.asyncio
async def test_get_commits_by_branch_success_with_pagination(mocked_api):
    """When page/size provided, API returns pagination wrapper; meta includes pagination fields."""
    response_body = {"pagination": SAMPLE_PAGINATION, "data": SAMPLE_COMMITS}
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json=response_body)
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID, page=1, size=25)

    assert result["success"] is True
    assert result["data"] == SAMPLE_COMMITS
    assert result["meta"]["page"] == 1
    assert result["meta"]["page_size"] == 25
    assert result["meta"]["page_count"] == 1
    assert result["meta"]["total_count"] == 19
    assert result["meta"]["enable_previous"] is False
    assert result["meta"]["enable_next"] is False
    params = mocked_api.calls.last.request.url.params
    assert params.get("branchId") == BRANCH_ID
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_commits_by_branch_pagination_params(mocked_api):
    """page and size are passed to API and reflected in meta."""
    pagination_page2 = {**SAMPLE_PAGINATION, "page": 2, "perPage": 10}
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json={"pagination": pagination_page2, "data": SAMPLE_COMMITS})
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID, page=2, size=10)

    assert result["success"] is True
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 10
    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "2"
    assert params.get("size") == "10"


@pytest.mark.asyncio
async def test_get_commits_by_branch_size_cap(mocked_api):
    """Requested size above 100 is capped at 100 and sent to API; meta reflects API response."""
    pagination_100 = {**SAMPLE_PAGINATION, "perPage": 100}
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json={"pagination": pagination_100, "data": []})
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID, page=1, size=200)

    assert result["meta"]["page_size"] == 100
    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_commits_by_branch_wrapper_response_no_pagination(mocked_api):
    """API returning wrapper { data: [...] } without page/size is normalized; meta has count."""
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json={"data": SAMPLE_COMMITS})
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_COMMITS
    assert result["meta"]["count"] == 1


@pytest.mark.asyncio
async def test_get_commits_by_branch_only_page_uses_defaults(mocked_api):
    """When only page is provided, size defaults to 25."""
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(200, json={"pagination": SAMPLE_PAGINATION, "data": []})
    )

    await get_commits_by_branch(branch_id=BRANCH_ID, page=1)

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "1"
    assert params.get("size") == "25"


@pytest.mark.asyncio
async def test_get_commits_by_branch_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/build/v2/commits/").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_commits_by_branch(branch_id=BRANCH_ID)

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_commits_by_branch"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
