"""Unit tests for get_bundle_identifiers: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.signing_identities.get_bundle_identifiers import get_bundle_identifiers

# Mock data for tests (no real org/credential identifiers)
SAMPLE_BUNDLE_IDS = [
    {
        "id": "aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "TestAppiOS",
        "appStoreId": "MOCKSTORE1",
        "identifier": "com.example.testapp",
        "platform": None,
        "storeCredentialId": "aaaaaaaa-0002-0000-0000-000000000002",
        "capabilities": [],
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "aaaaaaaa-0003-0000-0000-000000000003",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "TestApp Universal",
        "appStoreId": "MOCKSTORE2",
        "identifier": "com.example.hello-world",
        "platform": "UNIVERSAL",
        "storeCredentialId": "aaaaaaaa-0002-0000-0000-000000000002",
        "capabilities": [
            {
                "attributes": {
                    "capabilityType": "IN_APP_PURCHASE",
                    "settings": [],
                }
            }
        ],
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_bundle_identifiers_success(mocked_api):
    """Returns success envelope with data (list of bundle identifiers) and meta count when API returns list."""
    mocked_api.get("/signing-identity/v2/bundle-identifier").mock(
        return_value=Response(200, json=SAMPLE_BUNDLE_IDS)
    )

    result = await get_bundle_identifiers()

    assert result["success"] is True
    assert result["data"] == SAMPLE_BUNDLE_IDS
    assert len(result["data"]) == 2
    assert result["data"][0]["identifier"] == "com.example.testapp"
    assert result["data"][0]["name"] == "TestAppiOS"
    assert result["data"][1]["platform"] == "UNIVERSAL"
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.path == "/signing-identity/v2/bundle-identifier"


@pytest.mark.asyncio
async def test_get_bundle_identifiers_empty_list(mocked_api):
    """Returns success with empty data list and count 0 when API returns empty list."""
    mocked_api.get("/signing-identity/v2/bundle-identifier").mock(
        return_value=Response(200, json=[])
    )

    result = await get_bundle_identifiers()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_bundle_identifiers_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data/bundleIdentifiers) is normalized to list in data."""
    mocked_api.get("/signing-identity/v2/bundle-identifier").mock(
        return_value=Response(200, json={"data": SAMPLE_BUNDLE_IDS})
    )

    result = await get_bundle_identifiers()

    assert result["success"] is True
    assert result["data"] == SAMPLE_BUNDLE_IDS
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_get_bundle_identifiers_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/signing-identity/v2/bundle-identifier").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_bundle_identifiers()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_bundle_identifiers"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
