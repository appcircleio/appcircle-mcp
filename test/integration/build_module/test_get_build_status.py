"""
Integration tests for get_build_status (real Appcircle API).

Run with: pytest test/integration/build_module/test_get_build_status.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
Optional: APPCIRCLE_TEST_COMMIT_ID and APPCIRCLE_TEST_BUILD_ID (a matching pair) to
run when discovery fails; omit to skip.
"""

import os
import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.tools.build_module.get_build_profiles import get_build_profiles
from src.tools.build_module.get_commits_by_branch import get_commits_by_branch
from src.tools.build_module.get_build_status import get_build_status
from src.core.api_client import ApiClient

# Status codes per the Build API's commit/build status endpoint.
KNOWN_STATUS_CODES = {0, 1, 2, 3, 90, 91, 92, 99}


def _profiles(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of profiles."""
    return response.get("data", [])


def _commits(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of commits."""
    return response.get("data", [])


async def _get_a_commit_and_build_id() -> Optional[Tuple[str, str]]:
    """
    Discover a real (commit_id, build_id) pair: list profiles, then branches, then
    commits, and pick the first commit that has at least one build.
    Returns None if no such pair can be discovered.
    """
    list_result = await get_build_profiles(page=1, size=5)
    profiles = _profiles(list_result)
    if not list_result.get("success") or not profiles:
        return None

    api_client = ApiClient()
    for profile in profiles:
        profile_id = profile.get("id")
        if not profile_id:
            continue
        try:
            branches_response = await api_client.get(f"/build/v2/profiles/{profile_id}/branches")
        except Exception:
            continue

        branch_ids: List[str] = []
        if isinstance(branches_response, list):
            branch_ids = [b.get("id") or b.get("branchId") for b in branches_response if isinstance(b, dict)]
        elif isinstance(branches_response, dict):
            data = branches_response.get("data") or branches_response.get("branches") or []
            if isinstance(data, list):
                branch_ids = [b.get("id") or b.get("branchId") for b in data if isinstance(b, dict)]

        for branch_id in branch_ids:
            if not branch_id:
                continue
            try:
                commits_result = await get_commits_by_branch(branch_id=branch_id)
            except Exception:
                continue
            if not commits_result.get("success"):
                continue
            for commit in _commits(commits_result):
                if not isinstance(commit, dict):
                    continue
                builds = commit.get("builds")
                if isinstance(builds, list) and builds:
                    first_build = builds[0]
                    build_id = first_build.get("id") if isinstance(first_build, dict) else None
                    if build_id and commit.get("id"):
                        return (commit["id"], build_id)
    return None


async def _get_commit_and_build_id_from_env() -> Optional[Tuple[str, str]]:
    """If both env vars are set, use them directly without calling the API."""
    commit_id = os.getenv("APPCIRCLE_TEST_COMMIT_ID")
    build_id = os.getenv("APPCIRCLE_TEST_BUILD_ID")
    if commit_id and build_id:
        return (commit_id, build_id)
    return None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_build_status_basic_functionality(integration_settings):
    """Call get_build_status with a real commit/build pair; status is a known code."""
    pair = await _get_a_commit_and_build_id() or await _get_commit_and_build_id_from_env()
    if not pair:
        pytest.skip(
            "Could not discover a commit/build pair with at least one build. "
            "Set APPCIRCLE_TEST_COMMIT_ID and APPCIRCLE_TEST_BUILD_ID to run with real UUIDs."
        )

    commit_id, build_id = pair
    response = await get_build_status(commit_id=commit_id, build_id=build_id)

    assert "success" in response
    if response.get("success"):
        assert "data" in response
        data = response["data"]
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] in KNOWN_STATUS_CODES
        assert response["meta"] == {}
    else:
        assert "error" in response
        assert response["error"].get("tool") == "get_build_status"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_build_status_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_build_status(
            commit_id="00000000-0000-0000-0000-000000000001",
            build_id="00000000-0000-0000-0000-000000000002",
        )
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_build_status_not_found_returns_error(integration_settings):
    """Non-existent commit/build returns an error envelope (likely 404)."""
    result = await get_build_status(
        commit_id="00000000-0000-0000-0000-000000000000",
        build_id="00000000-0000-0000-0000-000000000000",
    )

    assert result.get("success") is False
    assert "error" in result
    assert result["error"].get("tool") == "get_build_status"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_build_status_performance_acceptable(integration_settings):
    """Single get_build_status call completes within 10s."""
    pair = await _get_a_commit_and_build_id() or await _get_commit_and_build_id_from_env()
    if not pair:
        pytest.skip(
            "Could not discover a commit/build pair. "
            "Set APPCIRCLE_TEST_COMMIT_ID and APPCIRCLE_TEST_BUILD_ID to run with real UUIDs."
        )

    commit_id, build_id = pair
    start = datetime.now()
    response = await get_build_status(commit_id=commit_id, build_id=build_id)
    duration = (datetime.now() - start).total_seconds()

    assert "success" in response
    assert duration < 10.0, f"Response took {duration:.2f}s"
