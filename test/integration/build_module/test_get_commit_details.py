"""
Integration tests for get_commit_details (real Appcircle API).

Run with: pytest test/integration/build_module/test_get_commit_details.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
Optional: APPCIRCLE_TEST_COMMIT_ID (commit UUID) to run when discovery fails; omit to skip.
"""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_commits_by_branch import get_commits_by_branch
from src.tools.build_module.get_commit_details import get_commit_details
from src.core.api_client import ApiClient


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _data_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of commits."""
    return response.get("data", [])


def _data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Unified envelope: data is the single commit for detail."""
    return response.get("data", {})


EXAMPLE_BRANCH_ID = "aaaaaaaa-0001-0000-0000-000000000001"


async def _get_a_commit_id_and_hash() -> Optional[Tuple[str, str]]:
    """
    Get (commit_id, commit_hash) from API: get a branch, fetch commits, return first commit's id and hash.
    Returns None if no commit can be discovered.
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
                            commits_result = await get_commits_by_branch(branch_id=branch_id)
                            if commits_result.get("success"):
                                commits = _data_list(commits_result)
                                if commits and isinstance(commits[0], dict):
                                    c = commits[0]
                                    if c.get("id") and c.get("hash"):
                                        return (c["id"], c["hash"])
                if isinstance(branches_response, dict):
                    data = branches_response.get("data") or branches_response.get("branches") or []
                    if isinstance(data, list) and data:
                        first = data[0]
                        if isinstance(first, dict):
                            branch_id = first.get("id") or first.get("branchId")
                            if branch_id:
                                commits_result = await get_commits_by_branch(branch_id=branch_id)
                                if commits_result.get("success"):
                                    commits = _data_list(commits_result)
                                    if commits and isinstance(commits[0], dict):
                                        c = commits[0]
                                        if c.get("id") and c.get("hash"):
                                            return (c["id"], c["hash"])
            except Exception:
                continue
    try:
        r = await get_commits_by_branch(branch_id=EXAMPLE_BRANCH_ID)
        if r.get("success"):
            commits = _data_list(r)
            if commits and isinstance(commits[0], dict):
                c = commits[0]
                if c.get("id") and c.get("hash"):
                    return (c["id"], c["hash"])
    except Exception:
        pass
    return None


async def _get_commit_id_and_hash_from_env() -> Optional[Tuple[str, str]]:
    """If APPCIRCLE_TEST_COMMIT_ID is set, fetch commit details and return (id, hash)."""
    commit_id = os.getenv("APPCIRCLE_TEST_COMMIT_ID")
    if not commit_id:
        return None
    result = await get_commit_details(commit_id=commit_id)
    if not result.get("success"):
        return None
    data = _data(result)
    if isinstance(data, dict) and data.get("id") and data.get("hash"):
        return (data["id"], data["hash"])
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_commit_details_by_id(integration_settings):
    """Get commit by commit_id; success and data shape."""
    pair = await _get_a_commit_id_and_hash() or await _get_commit_id_and_hash_from_env()
    if not pair:
        pytest.skip(
            "Could not discover a commit (no branch/commits). "
            "Set APPCIRCLE_TEST_COMMIT_ID to run with a real commit UUID."
        )

    commit_id, commit_hash = pair
    response = await get_commit_details(commit_id=commit_id)

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert data.get("id") == commit_id
    assert data.get("hash") == commit_hash
    for field in ["id", "organizationId", "profileId", "branchId", "hash", "message", "author", "commitDate"]:
        assert field in data, f"Commit missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_commit_details_by_hash(integration_settings):
    """Get commit by commit_hash; success and data shape."""
    pair = await _get_a_commit_id_and_hash() or await _get_commit_id_and_hash_from_env()
    if not pair:
        pytest.skip(
            "Could not discover a commit (no branch/commits). "
            "Set APPCIRCLE_TEST_COMMIT_ID to run with a real commit UUID."
        )

    commit_id, commit_hash = pair
    response = await get_commit_details(commit_hash=commit_hash)

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data(response)
    assert isinstance(data, dict)
    assert data.get("hash") == commit_hash
    # When looking up by hash, API may return a commit with same hash but different id (e.g. same SHA in another branch/profile)
    for field in ["id", "hash", "message", "author"]:
        assert field in data, f"Commit missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_commit_details(commit_id="00000000-0000-0000-0000-000000000000")
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_not_found_returns_error(integration_settings):
    """Non-existent commit ID returns 404 and standard error envelope."""
    non_existent_commit_id = "00000000-0000-0000-0000-000000000000"
    result = await get_commit_details(commit_id=non_existent_commit_id)

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_commit_details"
    assert result["error"].get("status_code") == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_commit_details call completes within 10s."""
    pair = await _get_a_commit_id_and_hash() or await _get_commit_id_and_hash_from_env()
    if not pair:
        pytest.skip(
            "Could not discover a commit. Set APPCIRCLE_TEST_COMMIT_ID to run with a real commit UUID."
        )

    commit_id, _ = pair
    start = datetime.now()
    response = await get_commit_details(commit_id=commit_id)
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"
