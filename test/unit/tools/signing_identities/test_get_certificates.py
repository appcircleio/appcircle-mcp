"""Unit tests for get_certificates: success and error envelope with mocked API."""

import pytest
from httpx import Response

from src.tools.signing_identities.get_certificates import get_certificates

# Sample certificates including fields we pop (p12Password, p12Binary, metaData, thumbprint)
SAMPLE_CERTIFICATES_RAW = [
    {
        "id": "cert-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "iOS Distribution",
        "type": "DISTRIBUTION",
        "p12Password": "secret123",
        "p12Binary": "base64encodedp12data...",
        "metaData": {"uploadedBy": "user@example.com"},
        "thumbprint": "abc123thumbprint",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "cert-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Development",
        "type": "DEVELOPMENT",
        "p12Password": "dev-secret",
        "p12Binary": "base64...",
        "metaData": None,
        "thumbprint": "def456",
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]

# Expected after trimming (excluded keys removed)
SAMPLE_CERTIFICATES_TRIMMED = [
    {
        "id": "cert-aaaaaaaa-0001-0000-0000-000000000001",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "iOS Distribution",
        "type": "DISTRIBUTION",
        "createDate": "2025-02-27T12:32:10.6316884+00:00",
    },
    {
        "id": "cert-aaaaaaaa-0002-0000-0000-000000000002",
        "organizationId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "name": "Development",
        "type": "DEVELOPMENT",
        "createDate": "2025-03-04T11:05:19.1612115+00:00",
    },
]


@pytest.mark.asyncio
async def test_get_certificates_success(mocked_api):
    """Returns success envelope with data (list of certificates) and meta count; excluded keys are popped."""
    mocked_api.get("/signing-identity/v2/certificates").mock(
        return_value=Response(200, json=SAMPLE_CERTIFICATES_RAW)
    )

    result = await get_certificates()

    assert result["success"] is True
    assert result["data"] == SAMPLE_CERTIFICATES_TRIMMED
    assert len(result["data"]) == 2
    assert result["data"][0]["name"] == "iOS Distribution"
    assert result["data"][0]["type"] == "DISTRIBUTION"
    assert "p12Password" not in result["data"][0]
    assert "p12Binary" not in result["data"][0]
    assert "metaData" not in result["data"][0]
    assert "thumbprint" not in result["data"][0]
    assert result["data"][1]["name"] == "Development"
    assert "p12Password" not in result["data"][1]
    assert result["meta"]["count"] == 2
    assert mocked_api.calls.last.request.url.path == "/signing-identity/v2/certificates"


@pytest.mark.asyncio
async def test_get_certificates_empty_list(mocked_api):
    """Returns success with empty data list and count 0 when API returns empty list."""
    mocked_api.get("/signing-identity/v2/certificates").mock(
        return_value=Response(200, json=[])
    )

    result = await get_certificates()

    assert result["success"] is True
    assert result["data"] == []
    assert result["meta"]["count"] == 0


@pytest.mark.asyncio
async def test_get_certificates_wrapper_response(mocked_api):
    """API returning wrapper (e.g. data/certificates) is normalized to list in data; excluded keys still popped."""
    mocked_api.get("/signing-identity/v2/certificates").mock(
        return_value=Response(200, json={"data": SAMPLE_CERTIFICATES_RAW})
    )

    result = await get_certificates()

    assert result["success"] is True
    assert result["data"] == SAMPLE_CERTIFICATES_TRIMMED
    assert result["meta"]["count"] == 2
    for cert in result["data"]:
        assert "p12Password" not in cert
        assert "p12Binary" not in cert
        assert "metaData" not in cert
        assert "thumbprint" not in cert


@pytest.mark.asyncio
async def test_get_certificates_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    mocked_api.get("/signing-identity/v2/certificates").mock(
        return_value=Response(500, json={"message": "Internal server error"})
    )

    result = await get_certificates()

    assert result["success"] is False
    assert "error" in result
    assert result["error"]["tool"] == "get_certificates"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
    assert "message" in result["error"]
