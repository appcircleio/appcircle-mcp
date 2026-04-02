"""Unit tests for ApiClient: GET, POST, PATCH, PUT, DELETE with mocked API."""

import pytest
from httpx import Response

from src.core.api_client import ApiClient


class TestApiClientInit:
    """Tests for ApiClient initialization from settings."""

    def test_init_uses_settings(self):
        """Client uses base_url, timeout, and auth header from settings."""
        client = ApiClient()
        assert client.base_url == "https://api.appcircle.io"
        assert client.timeout == 300
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-token-for-unit-tests"
        assert client.headers["Content-Type"] == "application/json"

    def test_init_uses_contextvar_token_over_settings(self):
        """When contextvar is set, ApiClient uses it instead of settings."""
        from src.core.auth import set_request_token, reset_request_token

        tok = set_request_token("per-request-token")
        try:
            client = ApiClient()
            assert client.headers["Authorization"] == "Bearer per-request-token"
        finally:
            reset_request_token(tok)


@pytest.mark.asyncio
class TestApiClientGet:
    """Tests for ApiClient.get."""

    async def test_get_success(self, mocked_api):
        """GET returns JSON when API returns 200."""
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json=[{"id": "1", "name": "Profile"}])
        )
        client = ApiClient()
        result = await client.get("/build/v2/profiles")
        assert result == [{"id": "1", "name": "Profile"}]

    async def test_get_with_params(self, mocked_api):
        """GET forwards query params to the API."""
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json=[])
        )
        client = ApiClient()
        await client.get("/build/v2/profiles", params={"page": "1", "size": "10"})
        call = mocked_api.calls.last
        assert call.request.url.params["page"] == "1"
        assert call.request.url.params["size"] == "10"

    async def test_get_raises_on_4xx(self, mocked_api):
        """GET raises HTTPStatusError when API returns 4xx."""
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(401, json={"message": "Unauthorized"})
        )
        client = ApiClient()
        with pytest.raises(Exception):  # httpx.HTTPStatusError
            await client.get("/build/v2/profiles")

    async def test_get_raises_on_5xx(self, mocked_api):
        """GET raises HTTPStatusError when API returns 5xx."""
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(500, json={"message": "Internal error"})
        )
        client = ApiClient()
        with pytest.raises(Exception):
            await client.get("/build/v2/profiles")


@pytest.mark.asyncio
class TestApiClientPost:
    """Tests for ApiClient.post."""

    async def test_post_success_with_json(self, mocked_api):
        """POST with json_data returns JSON when API returns 200."""
        payload = {"name": "New Profile"}
        mocked_api.post("/build/v2/profiles").mock(
            return_value=Response(200, json={"id": "new-id", "name": "New Profile"})
        )
        client = ApiClient()
        result = await client.post("/build/v2/profiles", json_data=payload)
        assert result == {"id": "new-id", "name": "New Profile"}
        assert mocked_api.calls.last.request.content is not None

    async def test_post_without_json(self, mocked_api):
        """POST without json_data succeeds (e.g. empty body)."""
        mocked_api.post("/some/endpoint").mock(
            return_value=Response(200, json={"ok": True})
        )
        client = ApiClient()
        result = await client.post("/some/endpoint")
        assert result == {"ok": True}

    async def test_post_with_files_removes_content_type(self, mocked_api):
        """POST with files does not send Content-Type (httpx sets multipart)."""
        mocked_api.post("/upload").mock(
            return_value=Response(200, json={"uploaded": True})
        )
        client = ApiClient()
        # Simulate file upload: pass files dict; client should pop Content-Type
        await client.post("/upload", files={"file": ("name", b"content")})
        # Header should not be application/json when files are present
        headers = mocked_api.calls.last.request.headers
        # When files are used, httpx sets multipart boundary; we just check no JSON content-type
        # Our code pops Content-Type so boundary is set by httpx
        assert "multipart/form-data" in headers.get("content-type", "")

    async def test_post_raises_on_4xx(self, mocked_api):
        """POST raises when API returns 4xx."""
        mocked_api.post("/build/v2/profiles").mock(
            return_value=Response(400, json={"message": "Bad request"})
        )
        client = ApiClient()
        with pytest.raises(Exception):
            await client.post("/build/v2/profiles", json_data={"x": 1})


@pytest.mark.asyncio
class TestApiClientPatch:
    """Tests for ApiClient.patch."""

    async def test_patch_success(self, mocked_api):
        """PATCH with json_data returns JSON when API returns 200."""
        payload = {"name": "Updated"}
        mocked_api.patch("/build/v2/profiles/123").mock(
            return_value=Response(200, json={"id": "123", "name": "Updated"})
        )
        client = ApiClient()
        result = await client.patch("/build/v2/profiles/123", json_data=payload)
        assert result["name"] == "Updated"

    async def test_patch_without_json(self, mocked_api):
        """PATCH without json_data succeeds."""
        mocked_api.patch("/build/v2/profiles/123").mock(
            return_value=Response(200, json={"id": "123"})
        )
        client = ApiClient()
        result = await client.patch("/build/v2/profiles/123")
        assert result == {"id": "123"}

    async def test_patch_raises_on_404(self, mocked_api):
        """PATCH raises when API returns 404."""
        mocked_api.patch("/build/v2/profiles/999").mock(
            return_value=Response(404, json={"message": "Not found"})
        )
        client = ApiClient()
        with pytest.raises(Exception):
            await client.patch("/build/v2/profiles/999", json_data={})


@pytest.mark.asyncio
class TestApiClientPut:
    """Tests for ApiClient.put."""

    async def test_put_success(self, mocked_api):
        """PUT with json_data returns JSON when API returns 200."""
        payload = {"name": "Full Update"}
        mocked_api.put("/build/v2/profiles/123").mock(
            return_value=Response(200, json={"id": "123", "name": "Full Update"})
        )
        client = ApiClient()
        result = await client.put("/build/v2/profiles/123", json_data=payload)
        assert result["name"] == "Full Update"

    async def test_put_without_json(self, mocked_api):
        """PUT without json_data succeeds."""
        mocked_api.put("/build/v2/profiles/123").mock(
            return_value=Response(200, json={"id": "123"})
        )
        client = ApiClient()
        result = await client.put("/build/v2/profiles/123")
        assert result == {"id": "123"}

    async def test_put_raises_on_4xx(self, mocked_api):
        """PUT raises when API returns 4xx."""
        mocked_api.put("/build/v2/profiles/123").mock(
            return_value=Response(422, json={"message": "Validation failed"})
        )
        client = ApiClient()
        with pytest.raises(Exception):
            await client.put("/build/v2/profiles/123", json_data={})


@pytest.mark.asyncio
class TestApiClientDelete:
    """Tests for ApiClient.delete."""

    async def test_delete_success(self, mocked_api):
        """DELETE returns JSON when API returns 200."""
        mocked_api.delete("/build/v2/profiles/123").mock(
            return_value=Response(200, json={"deleted": True})
        )
        client = ApiClient()
        result = await client.delete("/build/v2/profiles/123")
        assert result == {"deleted": True}

    async def test_delete_raises_on_404(self, mocked_api):
        """DELETE raises when API returns 404."""
        mocked_api.delete("/build/v2/profiles/999").mock(
            return_value=Response(404, json={"message": "Not found"})
        )
        client = ApiClient()
        with pytest.raises(Exception):
            await client.delete("/build/v2/profiles/999")
