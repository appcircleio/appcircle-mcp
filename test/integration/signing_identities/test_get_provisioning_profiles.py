"""
Integration tests for get_provisioning_profiles (real Appcircle API).

Run with: pytest test/integration/signing_identities/test_get_provisioning_profiles.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.tools.signing_identities.get_provisioning_profiles import get_provisioning_profiles

# Keys that must never appear in tool response (sensitive / excluded)
EXCLUDED_KEYS = {
    "binary",
    "metaData",
    "certificateThumbPrints",
    "provisionedDevices",
    "connectApiKeyId",
}


def _data_list(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Unified envelope: data is the list of provisioning profiles."""
    return response.get("data", [])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality(integration_settings):
    """Call get_provisioning_profiles; success and data shape; excluded keys not present."""
    response = await get_provisioning_profiles()

    assert response.get("success"), response.get("error")
    assert "data" in response
    data = _data_list(response)
    assert isinstance(data, list)
    assert "meta" in response
    assert response["meta"].get("count") == len(data)
    for profile in data:
        for key in EXCLUDED_KEYS:
            assert key not in profile, f"Provisioning profile must not contain excluded key: {key}"
    if data:
        for field in ["id", "organizationId", "name", "createDate"]:
            assert field in data[0], f"Provisioning profile missing expected field: {field}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_app_id(integration_settings):
    """Call with app_id; success and meta.filters.app_id present."""
    response = await get_provisioning_profiles(app_id="com.example.test")

    assert response.get("success"), response.get("error")
    assert "meta" in response
    assert response["meta"].get("filters", {}).get("app_id") == "com.example.test"
    data = _data_list(response)
    assert isinstance(data, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """Invalid token yields standard error envelope (success false, error object)."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid_token_12345"
        result = await get_provisioning_profiles()
        if not result.get("success"):
            assert "error" in result
            assert "tool" in result["error"]
            assert "type" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = original


@pytest.mark.integration
@pytest.mark.asyncio
async def test_performance_acceptable(integration_settings):
    """Single get_provisioning_profiles call completes within 10s."""
    start = datetime.now()
    response = await get_provisioning_profiles()
    duration = (datetime.now() - start).total_seconds()

    assert response.get("success"), response.get("error")
    assert duration < 10.0, f"Response took {duration:.2f}s"
