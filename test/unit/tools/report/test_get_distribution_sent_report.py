"""Unit tests for get_distribution_sent_report with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_distribution_sent_report import get_distribution_sent_report


@pytest.mark.asyncio
async def test_get_distribution_sent_report_success(
    mocked_api, sample_distribution_sent_report_response
):
    """Returns success with data and pagination meta when API returns data."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    result = await get_distribution_sent_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is True
    assert "data" in result
    assert "meta" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["profileName"] == "Internal Testing"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 55
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert "filters" in meta
    assert meta["filters"]["start_date"] == "2024-01-01"
    assert meta["filters"]["end_date"] == "2024-01-31"


@pytest.mark.asyncio
async def test_get_distribution_sent_report_bare_call_no_dates(
    mocked_api, sample_distribution_sent_report_response
):
    """Call without start_date/end_date does not send startDate/endDate."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    result = await get_distribution_sent_report()

    params = mocked_api.calls.last.request.url.params
    assert "startDate" not in params
    assert "endDate" not in params
    assert params.get("page") == "1"
    assert params.get("size") == "50"
    assert result["success"] is True
    assert "data" in result
    assert "meta" in result
    assert result["meta"]["filters"]["start_date"] is None
    assert result["meta"]["filters"]["end_date"] is None


@pytest.mark.asyncio
async def test_get_distribution_sent_report_default_pagination(
    mocked_api, sample_distribution_sent_report_response
):
    """With dates, no page/size sends defaults page=1, size=50."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    await get_distribution_sent_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("page") == "1"
    assert params.get("size") == "50"


@pytest.mark.asyncio
async def test_get_distribution_sent_report_pagination_params(
    mocked_api, sample_distribution_sent_report_response
):
    """page and size are passed to API and reflected in meta."""
    sample_distribution_sent_report_response["pagination"] = {
        "page": 2,
        "perPage": 25,
        "pageCount": 3,
        "totalCount": 65,
        "enablePrevious": True,
        "enableNext": True,
    }
    sample_distribution_sent_report_response["data"] = []
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    result = await get_distribution_sent_report(
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
async def test_get_distribution_sent_report_filters(
    mocked_api, sample_distribution_sent_report_response
):
    """profile_name, os, organization_id are passed to API."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    await get_distribution_sent_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        profile_name="Internal Testing",
        os="ios",
        organization_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("profileName") == "Internal Testing"
    assert params.get("os") == "ios"
    assert params.get("organizationId") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_get_distribution_sent_report_os_android(
    mocked_api, sample_distribution_sent_report_response
):
    """os=android is passed to API."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    await get_distribution_sent_report(
        start_date="2024-01-01", end_date="2024-01-31", os="android"
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("os") == "android"


@pytest.mark.asyncio
async def test_get_distribution_sent_report_size_cap(
    mocked_api, sample_distribution_sent_report_response
):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(200, json=sample_distribution_sent_report_response)
    )

    await get_distribution_sent_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        size=200,
    )

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_distribution_sent_report_error_returns_unified_envelope(mocked_api):
    """On API error, returns standard error envelope."""
    mocked_api.get("/report/v2/distribute-sent").mock(
        return_value=Response(400, json={"message": "Invalid date range"})
    )

    result = await get_distribution_sent_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_distribution_sent_report"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 400
