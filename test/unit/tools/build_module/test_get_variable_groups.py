"""Unit tests for get_variable_groups: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.build_module.get_variable_groups import get_variable_groups

SAMPLE_VARIABLE_GROUPS = [
    {
        "id": "aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Android",
        "sharedSubOrganizationIds": [],
        "sharedToAllSubs": False,
        "variables": [
            {"key": "AC_COMPILE_SDK_VERSION", "value": "35", "isSecret": False, "isFile": False},
        ],
        "createDate": "2026-01-14T14:50:59.5082425+00:00",
        "updateDate": "2026-01-14T14:51:22.4802973+00:00",
    },
    {
        "id": "aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "GithubToken",
        "sharedSubOrganizationIds": [],
        "sharedToAllSubs": False,
        "variables": [
            {"key": "DANGER_GITHUB_API_TOKEN", "value": "", "isSecret": True, "isFile": False},
        ],
        "createDate": "2025-10-13T10:27:51.8980294+00:00",
        "updateDate": "2025-10-13T10:45:15.0434535+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_variable_groups_success(mocked_api):
    """Returns success envelope with data and count when API returns variable groups (unwrapped list)."""
    mocked_api.get("/build/v2/variable-groups").mock(
        return_value=Response(200, json=SAMPLE_VARIABLE_GROUPS)
    )

    result = await get_variable_groups()

    assert result["success"] is True
    assert result["data"] == SAMPLE_VARIABLE_GROUPS
    assert result["meta"] == {"count": 2}


@pytest.mark.asyncio
async def test_get_variable_groups_secret_values_redacted(mocked_api):
    """Secret variable values pass through as-is (already redacted by the API, not by this tool)."""
    mocked_api.get("/build/v2/variable-groups").mock(
        return_value=Response(200, json=SAMPLE_VARIABLE_GROUPS)
    )

    result = await get_variable_groups()

    github_group = next(g for g in result["data"] if g["name"] == "GithubToken")
    secret_var = github_group["variables"][0]
    assert secret_var["isSecret"] is True
    assert secret_var["value"] == ""


@pytest.mark.asyncio
async def test_get_variable_groups_empty_list(mocked_api):
    """API returning an empty list yields an empty data list and count 0."""
    mocked_api.get("/build/v2/variable-groups").mock(return_value=Response(200, json=[]))

    result = await get_variable_groups()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_variable_groups_wrapper_response(mocked_api):
    """API returning a { data: ... } wrapper is normalized to the underlying list."""
    mocked_api.get("/build/v2/variable-groups").mock(
        return_value=Response(200, json={"data": SAMPLE_VARIABLE_GROUPS})
    )

    result = await get_variable_groups()

    assert result["success"] is True
    assert result["data"] == SAMPLE_VARIABLE_GROUPS


@pytest.mark.asyncio
async def test_get_variable_groups_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/build/v2/variable-groups").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_variable_groups()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_variable_groups"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500


@pytest.mark.asyncio
async def test_get_variable_groups_unauthorized_returns_unified_envelope(mocked_api):
    """When API returns 401, tool returns standard error envelope."""
    mocked_api.get("/build/v2/variable-groups").mock(
        return_value=Response(401, json={"message": "Unauthorized"})
    )

    result = await get_variable_groups()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_variable_groups"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 401
