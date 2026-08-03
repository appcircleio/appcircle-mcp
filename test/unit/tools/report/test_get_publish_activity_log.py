"""Unit tests for get_publish_activity_log with mocked API."""

import pytest
from httpx import Response

from src.tools.report.get_publish_activity_log import (
    PUBLISH_ACTIVITY_ACTIONS,
    get_publish_activity_log,
)


@pytest.mark.asyncio
async def test_get_publish_activity_log_success(mocked_api, sample_publish_activity_log_response):
    """Returns success with data and pagination meta when API returns data."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    result = await get_publish_activity_log(start_date="2026-06-01", end_date="2026-06-30")

    assert result["success"] is True
    assert len(result["data"]) == 1
    assert result["data"][0]["profileName"] == "HelloWorldApp"
    meta = result["meta"]
    assert meta["count"] == 1
    assert meta["page"] == 1
    assert meta["page_size"] == 50
    assert meta["total_count"] == 65
    assert meta["total_pages"] == 2
    assert meta["has_more"] is True
    assert meta["next_page"] == 2
    assert meta["filters"]["start_date"] == "2026-06-01"
    assert meta["filters"]["end_date"] == "2026-06-30"


@pytest.mark.asyncio
async def test_get_publish_activity_log_bare_call_no_dates(mocked_api, sample_publish_activity_log_response):
    """Call without start_date/end_date does not send startDate/endDate; defaults page=1, size=50."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    result = await get_publish_activity_log()

    params = mocked_api.calls.last.request.url.params
    assert "startDate" not in params
    assert "endDate" not in params
    assert params.get("page") == "1"
    assert params.get("size") == "50"
    assert result["success"] is True
    assert result["meta"]["filters"]["start_date"] is None


@pytest.mark.asyncio
async def test_get_publish_activity_log_size_cap(mocked_api, sample_publish_activity_log_response):
    """Requested size above 100 is capped at 100."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    await get_publish_activity_log(size=500)

    assert mocked_api.calls.last.request.url.params.get("size") == "100"


@pytest.mark.asyncio
async def test_get_publish_activity_log_filters_passed(mocked_api, sample_publish_activity_log_response):
    """organization_id maps to 'organization', profile_name maps to 'profileName'; platform/email/action pass through as-is."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    result = await get_publish_activity_log(
        organization_id="org-uuid",
        platform="iOS",
        email="user@example.com",
        profile_name="HelloWorldApp",
        action=36,
    )

    params = mocked_api.calls.last.request.url.params
    assert params.get("organization") == "org-uuid"
    assert "organizationId" not in params
    assert params.get("platform") == "iOS"
    assert params.get("email") == "user@example.com"
    assert params.get("profileName") == "HelloWorldApp"
    assert params.get("action") == "36"

    filters = result["meta"]["filters"]
    assert filters["organization_id"] == "org-uuid"
    assert filters["platform"] == "iOS"
    assert filters["email"] == "user@example.com"
    assert filters["profile_name"] == "HelloWorldApp"
    assert filters["action"] == 36


@pytest.mark.asyncio
async def test_get_publish_activity_log_known_action_codes(mocked_api, sample_publish_activity_log_response):
    """A known action code (e.g. 39=Re-sign failed) is sent as-is."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )
    assert PUBLISH_ACTIVITY_ACTIONS[39] == "Re-sign failed"

    result = await get_publish_activity_log(action=39)

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params.get("action") == "39"


@pytest.mark.asyncio
async def test_get_publish_activity_log_unknown_action_code_still_sent(mocked_api, sample_publish_activity_log_response):
    """An action code outside PUBLISH_ACTIVITY_ACTIONS is still forwarded to the API (not rejected)."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    result = await get_publish_activity_log(action=99999)

    assert result["success"] is True
    assert mocked_api.calls.last.request.url.params.get("action") == "99999"


@pytest.mark.asyncio
async def test_get_publish_activity_log_invalid_date_range(mocked_api):
    """start_date after end_date returns a validation_error without calling the API."""
    result = await get_publish_activity_log(start_date="2026-06-30", end_date="2026-06-01")

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_activity_log"
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_publish_activity_log_malformed_date_returns_validation_error(mocked_api):
    """A malformed start_date returns a validation_error without calling the API."""
    result = await get_publish_activity_log(start_date="not-a-date")

    assert result["success"] is False
    assert result["error"]["type"] == "validation_error"
    assert not mocked_api.calls


@pytest.mark.asyncio
async def test_get_publish_activity_log_page_below_one_defaults_to_one(mocked_api, sample_publish_activity_log_response):
    """page=0 (or negative) is clamped to 1, not sent as-is."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    await get_publish_activity_log(page=0)

    assert mocked_api.calls.last.request.url.params.get("page") == "1"


@pytest.mark.asyncio
async def test_get_publish_activity_log_size_below_one_defaults_to_one(mocked_api, sample_publish_activity_log_response):
    """size=-1 (or 0) is clamped to 1, not sent as-is."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(200, json=sample_publish_activity_log_response)
    )

    await get_publish_activity_log(size=-1)

    assert mocked_api.calls.last.request.url.params.get("size") == "1"


@pytest.mark.asyncio
async def test_get_publish_activity_log_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/report/v2/publish/activity").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_publish_activity_log()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_activity_log"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
