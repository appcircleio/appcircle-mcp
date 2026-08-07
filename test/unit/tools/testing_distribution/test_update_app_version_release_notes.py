"""Unit tests for update_app_version_release_notes: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.testing_distribution.update_app_version_release_notes import (
    update_app_version_release_notes,
)

PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
APP_VERSION_ID = "aaaaaaaa-0002-0000-0000-000000000002"
ENDPOINT = f"/distribution/v3/profiles/{PROFILE_ID}/app-versions/{APP_VERSION_ID}/message"
MESSAGE = "Bug fixes and improvements"


@pytest.fixture
def sample_app_version_response():
    return {
        "id": APP_VERSION_ID,
        "profileId": PROFILE_ID,
        "name": "Appcircle Sample",
        "version": "1.0",
        "versionCode": "2",
        "message": MESSAGE,
        "commitHash": "98dc06f6xx54e6d00b",
        "certThumbPrints": "221xxxx4288438B",
    }


@pytest.mark.asyncio
async def test_update_app_version_release_notes_success(mocked_api, sample_app_version_response):
    """Returns success envelope with the updated app version object, excluding certThumbPrints."""
    mocked_api.patch(ENDPOINT).mock(return_value=Response(200, json=sample_app_version_response))

    result = await update_app_version_release_notes(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE
    )

    expected = dict(sample_app_version_response)
    expected.pop("certThumbPrints")

    assert result["success"] is True
    assert result["data"] == expected
    assert "certThumbPrints" in sample_app_version_response
    assert "commitHash" in result["data"]
    assert result["meta"] == {}


@pytest.mark.asyncio
async def test_update_app_version_release_notes_sends_message_body(mocked_api, sample_app_version_response):
    """The message is sent as the JSON body."""
    route = mocked_api.patch(ENDPOINT).mock(return_value=Response(200, json=sample_app_version_response))

    await update_app_version_release_notes(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE
    )

    import json

    assert json.loads(route.calls.last.request.content) == {"message": MESSAGE}


@pytest.mark.asyncio
async def test_update_app_version_release_notes_409_maps_to_invalid_state(mocked_api):
    """HTTP 409 maps to type invalid_state, not http_error."""
    mocked_api.patch(ENDPOINT).mock(
        return_value=Response(409, json={"message": "App version is locked"})
    )

    result = await update_app_version_release_notes(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "update_app_version_release_notes"
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 409


@pytest.mark.asyncio
async def test_update_app_version_release_notes_422_maps_to_invalid_state(mocked_api):
    """HTTP 422 maps to type invalid_state."""
    mocked_api.patch(ENDPOINT).mock(return_value=Response(422, json={"message": "Invalid message"}))

    result = await update_app_version_release_notes(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE
    )

    assert result["success"] is False
    assert result["error"]["type"] == "invalid_state"
    assert result["error"]["status_code"] == 422


@pytest.mark.asyncio
async def test_update_app_version_release_notes_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.patch(ENDPOINT).mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await update_app_version_release_notes(
        profile_id=PROFILE_ID, app_version_id=APP_VERSION_ID, message=MESSAGE
    )

    assert result["success"] is False
    assert result["error"]["tool"] == "update_app_version_release_notes"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
