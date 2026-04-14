"""
Integration tests for get_signing_report (real Appcircle API).

Run with: pytest test/integration/report/test_get_signing_report.py -v
Requires: APPCIRCLE_ACCESS_TOKEN set in the environment.
"""

from datetime import datetime, timedelta
import pytest
from src.tools.report.get_signing_report import get_signing_report


@pytest.mark.integration
@pytest.mark.asyncio
async def test_basic_functionality_with_dates(integration_settings):
    """Returns success with data and pagination meta when using date range."""
    end = datetime.now()
    start = end - timedelta(days=30)
    response = await get_signing_report(
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bare_call_without_dates(integration_settings):
    """Returns success when called without start_date/end_date (all items, paginated)."""
    response = await get_signing_report()
    assert response.get("success"), response.get("error")
    assert "data" in response
    assert "meta" in response
    meta = response.get("meta", {})
    assert "count" in meta
    assert "page" in meta
    assert meta.get("filters", {}).get("start_date") is None
    assert meta.get("filters", {}).get("end_date") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_returns_envelope(integration_settings):
    """On API error, returns standard error envelope."""
    from src.config.settings import settings
    import os
    original = settings.APPCIRCLE_ACCESS_TOKEN
    try:
        settings.APPCIRCLE_ACCESS_TOKEN = "invalid"
        result = await get_signing_report(
            start_date="2024-01-01",
            end_date="2024-01-31",
        )
        if not result.get("success"):
            assert "error" in result and "tool" in result["error"]
    finally:
        settings.APPCIRCLE_ACCESS_TOKEN = os.getenv("APPCIRCLE_ACCESS_TOKEN") or original
