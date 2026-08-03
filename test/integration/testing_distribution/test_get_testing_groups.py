"""
Integration tests for get_testing_groups (real Appcircle API).

Run with: pytest test/integration/testing_distribution/test_get_testing_groups.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest

from src.tools.testing_distribution.get_testing_groups import get_testing_groups


def _groups(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of testing groups."""
    return response.get("data", [])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Response has success, data, meta; data is a list; count in meta matches."""
    response = await get_testing_groups()
    assert isinstance(response, dict), "Response must be a dict"
    assert "success" in response
    assert response["success"] is True, response.get("error")
    groups = _groups(response)
    assert isinstance(groups, list)
    assert response["meta"]["count"] == len(groups)
    if groups:
        for field in ["id", "name", "testers", "groupType"]:
            assert field in groups[0], f"Testing group missing field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_integrity(integration_settings):
    """Group IDs are unique; testers is always a list."""
    response = await get_testing_groups()
    if not response.get("success") or not _groups(response):
        pytest.skip("No testing groups to validate")
    groups = _groups(response)
    ids = [g["id"] for g in groups]
    assert len(ids) == len(set(ids)), "Duplicate testing group IDs"
    for group in groups:
        assert isinstance(group.get("testers"), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_testing_groups()
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single call completes within 10s."""
    start = datetime.now()
    response = await get_testing_groups()
    duration = (datetime.now() - start).total_seconds()
    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"
