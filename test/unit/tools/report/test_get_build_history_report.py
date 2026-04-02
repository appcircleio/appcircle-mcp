"""Unit tests for get_build_history_report with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_build_history_report import get_build_history_report


@pytest.mark.asyncio
async def test_get_build_history_report_success(mocked_api, sample_build_history_response):
    """Returns success with data and pagination meta when API returns data."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    result = await get_build_history_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is True
    assert "data" in result
    assert "meta" in result
    assert len(result["data"]) == 1
    assert result["data"][0]["buildProfileName"] == "iOS Build"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 75
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert "filters" in meta
    assert meta["filters"]["start_date"] == "2024-01-01"
    assert meta["filters"]["end_date"] == "2024-01-31"


@pytest.mark.asyncio
async def test_get_build_history_report_bare_call_no_dates(mocked_api, sample_build_history_response):
    """Call without start_date/end_date does not send startDate/endDate; returns all items (paginated)."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    result = await get_build_history_report()

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
async def test_get_build_history_report_default_pagination(mocked_api, sample_build_history_response):
    """With dates, no page/size sends defaults page=1, size=50."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    await get_build_history_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("page") == "1"
    assert params.get("size") == "50"


@pytest.mark.asyncio
async def test_get_build_history_report_pagination_params(mocked_api, sample_build_history_response):
    """page and size are passed to API and reflected in meta."""
    sample_build_history_response["pagination"] = {
        "page": 2,
        "perPage": 25,
        "pageCount": 4,
        "totalCount": 100,
        "enablePrevious": True,
        "enableNext": True,
    }
    sample_build_history_response["data"] = []
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    result = await get_build_history_report(
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
async def test_get_build_history_report_filters(mocked_api, sample_build_history_response):
    """build_profile_name and organization_id are passed as buildProfileName and organizationId."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    await get_build_history_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        build_profile_name="iOS Build",
        organization_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("startDate") == "2024-01-01"
    assert params.get("endDate") == "2024-01-31"
    assert params.get("buildProfileName") == "iOS Build"
    assert params.get("organizationId") == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.mark.asyncio
async def test_get_build_history_report_size_cap(mocked_api, sample_build_history_response):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(200, json=sample_build_history_response)
    )

    await get_build_history_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
        size=200,
    )

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_build_history_report_error_returns_unified_envelope(mocked_api):
    """On API error, returns standard error envelope."""
    mocked_api.get("/report/v2/build").mock(
        return_value=Response(400, json={"message": "Invalid date range"})
    )

    result = await get_build_history_report(
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_history_report"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 400
