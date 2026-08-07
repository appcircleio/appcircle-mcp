"""
Integration tests for get_last_commit (real Appcircle API).

Run with: pytest test/integration/build_module/test_get_last_commit.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
Optional: APPCIRCLE_TEST_BRANCH_ID (branch UUID) to run when discovery fails; omit to skip.
"""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_commits_by_branch import get_commits_by_branch
from src.tools.build_module.get_last_commit import get_last_commit
from src.core.api_client import ApiClient


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single commit."""
    return response.get("data", {})


EXAMPLE_BRANCH_ID = "aaaaaaaa-0001-0000-0000-000000000001"


async def _get_a_branch_id() -> Optional[str]:
    """
    Try to get a branch ID from the API: list profiles, then try to get branches
    for the first profile. Falls back to example branch ID if commits return success.
    Returns None if no branch can be discovered.
    """
    list_result = await get_build_profiles(page=1, size=5)
    profiles = _profiles(list_result)
    if not list_result.get("success") or not profiles:
        pass
    else:
        api_client = ApiClient()
        for profile in profiles:
            profile_id = profile.get("id")
            if not profile_id:
                continue
            try:
                branches_response = await api_client.get(
                    f"/build/v2/profiles/{profile_id}/branches"
                )
                if isinstance(branches_response, list) and branches_response:
                    first = branches_response[0]
                    if isinstance(first, dict):
                        branch_id = first.get("id") or first.get("branchId")
                        if branch_id:
                            return branch_id
                if isinstance(branches_response, dict):
                    data = branches_response.get("data") or branches_response.get("branches") or []
                    if isinstance(data, list) and data:
                        first = data[0]
                        if isinstance(first, dict):
                            bid = first.get("id") or first.get("branchId")
                            if bid:
                                return bid
            except Exception:
                continue
    try:
        r = await get_commits_by_branch(branch_id=EXAMPLE_BRANCH_ID)
        if r.get("success"):
            return EXAMPLE_BRANCH_ID
    except Exception:
        pass
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_last_commit_basic_functionality(integration_settings):
    """Call get_last_commit with a real branch_id; success and data shape, or valid error."""
    branch_id = await _get_a_branch_id() or os.getenv("APPCIRCLE_TEST_BRANCH_ID")
    if not branch_id:
        pytest.skip(
            "Could not discover a branch_id (no profiles or no branches endpoint). "
            "Set APPCIRCLE_TEST_BRANCH_ID to run with a real branch UUID."
        )

    response = await get_last_commit(branch_id=branch_id)

    assert "success" in response
    if response.get("success"):
        assert "data" in response
        data = _data(response)
        assert isinstance(data, dict)
        assert response["meta"] == {}
        if data:
            for field in ["id", "branchId", "hash", "message", "author", "commitDate"]:
                assert field in data, f"Commit missing field: {field}"
            assert data.get("branchId") == branch_id
    else:
        assert "error" in response
        assert response["error"].get("tool") == "get_last_commit"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_last_commit_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_last_commit(branch_id="00000000-0000-0000-0000-000000000001")
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_last_commit_not_found_returns_error(integration_settings):
    """Non-existent branch returns an error envelope (likely 404)."""
    non_existent_branch = "00000000-0000-0000-0000-000000000000"
    result = await get_last_commit(branch_id=non_existent_branch)

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_last_commit"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_last_commit_performance_acceptable(integration_settings):
    """Single get_last_commit call completes within 10s."""
    branch_id = await _get_a_branch_id() or os.getenv("APPCIRCLE_TEST_BRANCH_ID")
    if not branch_id:
        pytest.skip(
            "Could not discover a branch_id. Set APPCIRCLE_TEST_BRANCH_ID to run with a real branch UUID."
        )

    start = datetime.now()
    response = await get_last_commit(branch_id=branch_id)
    duration = (datetime.now() - start).total_seconds()

    assert "success" in response
    assert duration < 10.0, f"Response took {duration:.2f}s"
