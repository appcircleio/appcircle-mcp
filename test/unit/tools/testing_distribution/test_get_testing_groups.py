"""Unit tests for get_testing_groups: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.testing_distribution.get_testing_groups import get_testing_groups

SAMPLE_TESTING_GROUPS = [
    {
        "id": "aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "CodePush Testers",
        "testers": ["tester1@example.com"],
        "groupType": 0,
        "createDate": "2025-05-26T12:38:47.9783499+00:00",
        "updateDate": "2025-05-26T12:38:47.9783499+00:00",
        "externalGroupName": None,
    },
    {
        "id": "aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "My Testers",
        "testers": ["tester2@example.com", "tester3@example.com"],
        "groupType": 0,
        "createDate": "2025-02-17T09:42:14.4011016+00:00",
        "updateDate": "2025-02-17T09:42:14.4011017+00:00",
        "externalGroupName": None,
    },
]


@pytest.mark.asyncio
async def test_get_testing_groups_success(mocked_api):
    """Returns success envelope with data and count when API returns testing groups (unwrapped list)."""
    mocked_api.get("/distribution/v2/testing-groups").mock(
        return_value=Response(200, json=SAMPLE_TESTING_GROUPS)
    )

    result = await get_testing_groups()

    assert result["success"] is True
    assert result["data"] == SAMPLE_TESTING_GROUPS
    assert result["meta"] == {"count": 2}


@pytest.mark.asyncio
async def test_get_testing_groups_empty_list(mocked_api):
    """API returning an empty list yields an empty data list and count 0."""
    mocked_api.get("/distribution/v2/testing-groups").mock(return_value=Response(200, json=[]))

    result = await get_testing_groups()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_testing_groups_wrapper_response(mocked_api):
    """API returning a { data: ... } wrapper is normalized to the underlying list."""
    mocked_api.get("/distribution/v2/testing-groups").mock(
        return_value=Response(200, json={"data": SAMPLE_TESTING_GROUPS})
    )

    result = await get_testing_groups()

    assert result["success"] is True
    assert result["data"] == SAMPLE_TESTING_GROUPS


@pytest.mark.asyncio
async def test_get_testing_groups_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/distribution/v2/testing-groups").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_testing_groups()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_testing_groups"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500


@pytest.mark.asyncio
async def test_get_testing_groups_unauthorized_returns_unified_envelope(mocked_api):
    """When API returns 401, tool returns standard error envelope."""
    mocked_api.get("/distribution/v2/testing-groups").mock(
        return_value=Response(401, json={"message": "Unauthorized"})
    )

    result = await get_testing_groups()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_testing_groups"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 401
