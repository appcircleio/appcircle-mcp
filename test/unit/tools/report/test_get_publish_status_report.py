"""Unit tests for get_publish_status_report with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_publish_status_report import get_publish_status_report


@pytest.mark.asyncio
async def test_get_publish_status_report_success(
    mocked_api, sample_publish_status_report_response
):
    """Returns success with data and pagination meta when API returns data."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    result = await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is True
    assert "data" in result
    assert "meta" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["appName"] == "MyApp"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 70
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert "filters" in meta
    assert meta["filters"]["start_date"] == "2024-01-01"
    assert meta["filters"]["end_date"] == "2024-01-31"


@pytest.mark.asyncio
async def test_get_publish_status_report_bare_call_no_dates(
    mocked_api, sample_publish_status_report_response
):
    """Call without start_date/end_date does not send startDate/endDate."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    result = await get_publish_status_report()

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
async def test_get_publish_status_report_default_pagination(
    mocked_api, sample_publish_status_report_response
):
    """With dates, no page/size sends defaults page=1, size=50."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("page") == "1"
    assert params.get("size") == "50"


@pytest.mark.asyncio
async def test_get_publish_status_report_pagination_params(
    mocked_api, sample_publish_status_report_response
):
    """page and size are passed to API and reflected in meta."""
    sample_publish_status_report_response["pagination"] = {
        "page": 2,
        "perPage": 25,
        "pageCount": 4,
        "totalCount": 100,
        "enablePrevious": True,
        "enableNext": True,
    }
    sample_publish_status_report_response["data"] = []
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    result = await get_publish_status_report(
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
async def test_get_publish_status_report_filters(
    mocked_api, sample_publish_status_report_response
):
    """app_name, organization_id, status are passed to API."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        app_name="MyApp",
        organization_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        status=0,
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("appName") == "MyApp"
    assert params.get("organizationId") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert params.get("status") == "0"


@pytest.mark.asyncio
async def test_get_publish_status_report_status_extended_values(
    mocked_api, sample_publish_status_report_response
):
    """Extended status values (200, 201, 202, 203) are passed to API."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        status=202,
    )

    assert mocked_api.calls.last.request.url.params.get("status") == "202"


@pytest.mark.asyncio
async def test_get_publish_status_report_size_cap(
    mocked_api, sample_publish_status_report_response
):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(200, json=sample_publish_status_report_response)
    )

    await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        size=200,
    )

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_publish_status_report_error_returns_unified_envelope(mocked_api):
    """On API error, returns standard error envelope."""
    mocked_api.get("/report/v1/publish/status").mock(
        return_value=Response(400, json={"message": "Invalid date range"})
    )

    result = await get_publish_status_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_status_report"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 400
