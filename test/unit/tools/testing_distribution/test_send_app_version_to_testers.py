"""Unit tests for send_app_version_to_testers: success and error envelope with mocked API."""

import json

import pytest
from httpx import Response

from src.tools.testing_distribution.send_app_version_to_testers import send_app_version_to_testers

PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"
ENDPOINT = f"/distribution/v2/profiles/{PROFILE_ID}/app-versions/{APP_VERSION_ID}"
TASK_ID = "aaaaaaaa-0003-0000-0000-000000000003"
MESSAGE = "New build ready"
TESTERS = ["tester@example.com"]


@pytest.mark.asyncio
async def test_send_app_version_to_testers_success(mocked_api):
    """Returns success envelope with taskId when API returns 202 Accepted."""
    route = mocked_api.post(ENDPOINT).mock(return_value=Response(202, json={"taskId": TASK_ID}))

    result = await send_app_version_to_testers(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE, testers=TESTERS
    )

    assert result["success"] is True
    assert result["data"] == {"taskId": TASK_ID}
    assert result["meta"]["profile_id"] == PROFILE_ID
    assert result["meta"]["app_version_id"] == APP_VERSION_ID
    assert result["meta"]["testers"] == TESTERS
    assert route.calls.last.request.url.params["action"] == "sendToTesting"
    assert json.loads(route.calls.last.request.content) == {"message": MESSAGE, "testers": TESTERS}


@pytest.mark.asyncio
async def test_send_app_version_to_testers_with_testing_group_id(mocked_api):
    """testers can contain a testing group ID instead of an email."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(202, json={"taskId": TASK_ID}))

    result = await send_app_version_to_testers(
        profile_id=PROFILE_ID,
        app_version_id=APP_VERSION_ID,
        message=MESSAGE,
        testers=["cccccccc-0001-0000-0000-000000000001"],
    )

    assert result["success"] is True
    assert result["meta"]["testers"] == ["cccccccc-0001-0000-0000-000000000001"]


@pytest.mark.asyncio
async def test_send_app_version_to_testers_409_maps_to_invalid_state(mocked_api):
    """HTTP 409 maps to type invalid_state, not http_error."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(409, json={"message": "App version is locked"})
    )

    result = await send_app_version_to_testers(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE, testers=TESTERS
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "send_app_version_to_testers"
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 409


@pytest.mark.asyncio
async def test_send_app_version_to_testers_422_maps_to_invalid_state(mocked_api):
    """HTTP 422 maps to type invalid_state."""
    mocked_api.post(ENDPOINT).mock(return_value=Response(422, json={"message": "Invalid testers"}))

    result = await send_app_version_to_testers(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE, testers=TESTERS
    )

    assert result["success"] is False
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 422


@pytest.mark.asyncio
async def test_send_app_version_to_testers_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.post(ENDPOINT).mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await send_app_version_to_testers(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE, testers=TESTERS
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "send_app_version_to_testers"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
