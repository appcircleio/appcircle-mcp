"""
Integration tests for get_publish_activity_log (real Appcircle API).

Run with: pytest test/integration/report/test_get_publish_activity_log.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from datetime import datetime, timedelta

import pytest

from src.tools.report.get_publish_activity_log import get_publish_activity_log


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_with_dates(integration_settings):
    """Returns success with data and pagination meta when using date range."""
    end = datetime.now()
    start = end - timedelta(days=30)
    response = await get_publish_activity_log(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    )
    assert response.get("success"), response.get("error")
    assert "data" in response
    meta = response.get("meta", {})
    assert "count" in meta
    assert "page" in meta
    assert meta.get("page_size") == 50


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bare_call_without_dates(integration_settings):
    """Returns success when called without start_date/end_date (all items, paginated)."""
    response = await get_publish_activity_log()
    assert response.get("success"), response.get("error")
    meta = response.get("meta", {})
    assert meta.get("filters", {}).get("start_date") is None
    assert meta.get("filters", {}).get("end_date") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_date_range_returns_validation_error(integration_settings):
    """start_date after end_date returns a validation_error without calling the API."""
    result = await get_publish_activity_log(start_date="2026-06-30", end_date="2026-06-01")
    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """On API error, returns standard error envelope."""
    import os

    from src.config.settings import settings

    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid"
        result = await get_publish_activity_log()
        if not result.get("success"):
            assert "error" in result and "tool" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = os.getenv("APPCIRCLE_ACCESS_TOKEN") or original
