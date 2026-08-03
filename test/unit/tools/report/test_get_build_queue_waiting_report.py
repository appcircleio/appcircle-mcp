"""Unit tests for get_build_queue_waiting_report with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_build_queue_waiting_report import get_build_queue_waiting_report


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_success(mocked_api, sample_build_queue_waiting_report_response):
    """Returns success with data, pagination meta, and summary when API returns data."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=sample_build_queue_waiting_report_response)
    )

    result = await get_build_queue_waiting_report(start_date="2026-06-01", end_date="2026-06-30")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["buildProfileName"] == "iOS Build"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 23
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert meta["filters"]["start_date"] == "2026-06-01"
    assert meta["filters"]["end_date"] == "2026-06-30"
    assert meta["summary"] == {"standard": 12.5, "velocity": 3.2, "ultra": 0.0}


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_bare_call_no_dates(mocked_api, sample_build_queue_waiting_report_response):
    """Call without start_date/end_date does not send startDate/endDate; defaults page=1, size=50."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=sample_build_queue_waiting_report_response)
    )

    result = await get_build_queue_waiting_report()

    params = mocked_api.calls.last.request.url.params
    assert "startDate" not in params
    assert "endDate" not in params
    assert params.get("page") == "1"
    assert params.get("size") == "50"
    assert result["success"] is True
    assert result["meta"]["filters"]["start_date"] is None


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_size_cap(mocked_api, sample_build_queue_waiting_report_response):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=sample_build_queue_waiting_report_response)
    )

    await get_build_queue_waiting_report(size=500)

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_missing_summary_defaults_to_none(mocked_api):
    """A response with no summary field yields meta.summary = None (not fabricated)."""
    response_without_summary = {
        "pagination": {
            "page": 1,
            "perPage": 50,
            "pageCount": 1,
            "totalCount": 0,
            "enablePrevious": False,
            "enableNext": False,
        },
        "data": [],
    }
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=response_without_summary)
    )

    result = await get_build_queue_waiting_report()

    assert result["success"] is True
    assert result["meta"]["summary"] is None


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_invalid_date_range(mocked_api):
    """start_date after end_date returns a validation_error without calling the API."""
    result = await get_build_queue_waiting_report(start_date="2026-06-30", end_date="2026-06-01")

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_queue_waiting_report"
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_malformed_date_returns_validation_error(mocked_api):
    """A malformed start_date returns a validation_error without calling the API."""
    result = await get_build_queue_waiting_report(start_date="not-a-date")

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_page_below_one_defaults_to_one(
    mocked_api, sample_build_queue_waiting_report_response
):
    """page=0 (or negative) is clamped to 1, not sent as-is."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=sample_build_queue_waiting_report_response)
    )

    await get_build_queue_waiting_report(page=0)

    assert mocked_api.calls.last.request.url.params.get("page") == "1"


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_size_below_one_defaults_to_one(
    mocked_api, sample_build_queue_waiting_report_response
):
    """size=-1 (or 0) is clamped to 1, not sent as-is."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(200, json=sample_build_queue_waiting_report_response)
    )

    await get_build_queue_waiting_report(size=-1)

    assert mocked_api.calls.last.request.url.params.get("size") == "1"


@pytest.mark.asyncio
async def test_get_build_queue_waiting_report_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/report/v1/build/queue-waiting").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_build_queue_waiting_report()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_queue_waiting_report"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
