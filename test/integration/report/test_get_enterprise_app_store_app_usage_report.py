"""
Integration tests for get_enterprise_app_store_app_usage_report (real Appcircle API).

Run with: pytest test/integration/report/test_get_enterprise_app_store_app_usage_report.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
Optional: APPCIRCLE_TEST_ORGANIZATION_ID (org UUID) to run test_with_organization_id; omit to skip it.
"""

import os
from datetime import datetime, timedelta
import pytest
from src.tools.report.get_enterprise_app_store_app_usage_report import (
    get_enterprise_app_store_app_usage_report,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_with_dates(integration_settings):
    """Returns success with data and pagination meta when using date range."""
    end = datetime.now()
    start = end - timedelta(days=30)
    response = await get_enterprise_app_store_app_usage_report(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    )
    assert response.get("success"), response.get("error")
    assert "data" in response
    assert "meta" in response
    meta = response.get("meta", {})
    assert "count" in meta
    assert "page" in meta
    assert "total_count" in meta
    assert meta.get("page_size") == 50
    assert meta.get("filters", {}).get("start_date") == start.strftime("%Y-%m-%d")
    assert meta.get("filters", {}).get("end_date") == end.strftime("%Y-%m-%d")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_organization_id(integration_settings):
    """Returns success when optional organization_id is provided (skipped unless APPCIRCLE_TEST_ORGANIZATION_ID is set)."""
    org_id = os.getenv("APPCIRCLE_TEST_ORGANIZATION_ID")
    if not org_id:
        pytest.skip(
            "APPCIRCLE_TEST_ORGANIZATION_ID not set; use a real org UUID to run this test (not committed for privacy)"
        )
    end = datetime.now()
    start = end - timedelta(days=7)
    response = await get_enterprise_app_store_app_usage_report(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        organization_id=org_id,
    )
    assert response.get("success"), response.get("error")
    assert "data" in response
    assert "meta" in response
    assert response.get("meta", {}).get("filters", {}).get("organization_id") == org_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """On API error, returns standard error envelope."""
    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid"
        result = await get_enterprise_app_store_app_usage_report(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        if not result.get("success"):
            assert "error" in result and "tool" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = os.getenv("APPCIRCLE_ACCESS_TOKEN") or original
