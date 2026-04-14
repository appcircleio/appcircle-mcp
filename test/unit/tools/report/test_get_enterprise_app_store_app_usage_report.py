"""Unit tests for get_enterprise_app_store_app_usage_report with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_enterprise_app_store_app_usage_report import (
    get_enterprise_app_store_app_usage_report,
)


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_success(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """Returns success with data and pagination meta when API returns data."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    result = await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is True
    assert "data" in result
    assert "meta" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["storeProfileName"] == "Internal Store"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 45
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert "filters" in meta
    assert meta["filters"]["start_date"] == "2024-01-01"
    assert meta["filters"]["end_date"] == "2024-01-31"


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_required_dates(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """startDate and endDate are always sent to API."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("page") == "1"
    assert params.get("size") == "50"


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_pagination_params(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """page and size are passed to API and reflected in meta."""
    sample_enterprise_app_store_app_usage_report_response["pagination"] = {
        "page": 2,
        "perPage": 25,
        "pageCount": 2,
        "totalCount": 50,
        "enablePrevious": True,
        "enableNext": False,
    }
    sample_enterprise_app_store_app_usage_report_response["data"] = []
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    result = await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        page=2,
        size=25,
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("page") == "2"
    assert params.get("size") == "25"
    assert result["meta"]["page"] == 2
    assert result["meta"]["page_size"] == 25


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_organization_filter(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """organization_id is passed as organizationId when provided."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        organization_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("organizationId") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_no_organization(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """organizationId is not in params when organization_id is omitted."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    params = mocked_api.calls.last.request.url.params
    assert "organizationId" not in params


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_size_cap(
    mocked_api, sample_enterprise_app_store_app_usage_report_response
):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(200, json=sample_enterprise_app_store_app_usage_report_response)
    )

    await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        size=200,
    )

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_enterprise_app_store_app_usage_report_error_returns_unified_envelope(
    mocked_api,
):
    """On API error, returns standard error envelope."""
    mocked_api.get("/store-report/v2/app-usage").mock(
        return_value=Response(400, json={"message": "Invalid date range"})
    )

    result = await get_enterprise_app_store_app_usage_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_enterprise_app_store_app_usage_report"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 400
