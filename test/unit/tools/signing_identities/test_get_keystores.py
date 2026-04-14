"""Unit tests for get_keystores: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.signing_identities.get_keystores import get_keystores

# Sample keystores including fields we pop (password, aliasPassword, binary, checkSum, sha256FingerPrint)
SAMPLE_KEYSTORES_RAW = [
    {
        "id": "ks-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Android Release",
        "password": "keystore-secret",
        "aliasPassword": "alias-secret",
        "binary": "base64keystore...",
        "checkSum": "checksum123",
        "sha256FingerPrint": "AA:BB:CC:DD:...",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "ks-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Android Debug",
        "password": "debug-pass",
        "aliasPassword": "debug-alias",
        "binary": "base64...",
        "checkSum": "sum456",
        "sha256FingerPrint": "EE:FF:00:11:...",
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]

# Expected after trimming (excluded keys removed)
SAMPLE_KEYSTORES_TRIMMED = [
    {
        "id": "ks-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Android Release",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "ks-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Android Debug",
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_keystores_success(mocked_api):
    """Returns success envelope with data (list of keystores) and meta count; excluded keys are popped."""
    mocked_api.get("/signing-identity/v2/keystores").mock(
        return_value=Response(200, json=SAMPLE_KEYSTORES_RAW)
    )

    result = await get_keystores()

    assert result["success"] is True
    assert result["data"] == SAMPLE_KEYSTORES_TRIMMED
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "Android Release"
    assert "password" not in result["data"][0]
    assert "aliasPassword" not in result["data"][0]
    assert "binary" not in result["data"][0]
    assert "checkSum" not in result["data"][0]
    assert "sha256FingerPrint" not in result["data"][0]
    assert result["data"][1]["name"] == "Android Debug"
    assert "password" not in result["data"][1]
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.path == "/signing-identity/v2/keystores"


@pytest.mark.asyncio
async def test_get_keystores_empty_list(mocked_api):
    """Returns success with empty data list and count 0 when API returns empty list."""
    mocked_api.get("/signing-identity/v2/keystores").mock(
        return_value=Response(200, json=[])
    )

    result = await get_keystores()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_keystores_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data/keystores) is normalized to list in data; excluded keys still popped."""
    mocked_api.get("/signing-identity/v2/keystores").mock(
        return_value=Response(200, json={"data": SAMPLE_KEYSTORES_RAW})
    )

    result = await get_keystores()

    assert result["success"] is True
    assert result["data"] == SAMPLE_KEYSTORES_TRIMMED
    assert result["meta"]["count"] == 2
    for ks in result["data"]:
        assert "password" not in ks
        assert "aliasPassword" not in ks
        assert "binary" not in ks
        assert "checkSum" not in ks
        assert "sha256FingerPrint" not in ks


@pytest.mark.asyncio
async def test_get_keystores_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/signing-identity/v2/keystores").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_keystores()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_keystores"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
