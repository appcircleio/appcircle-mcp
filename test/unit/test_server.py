"""Unit tests for server entry point (main) and related behavior."""

import os

import pytest
from unittest.mock import MagicMock, patch


class TestMain:
    """Tests for main() entry point."""

    def test_main_exits_when_access_token_missing(self, monkeypatch):
        """main() logs error and exits with 1 when APPCIRCLE_ACCESS_TOKEN is not set."""
        monkeypatch.delenv("APPCIRCLE_ACCESS_TOKEN", raising=False)
        exit_calls = []

        def fake_exit(code):
            exit_calls.append(code)
            raise SystemExit(code)

        with pytest.raises(SystemExit):
            with patch("src.server.sys.exit", side_effect=fake_exit):
                with patch("src.server.logger") as mock_logger:
                    import src.server as server_module
                    server_module.main()
        assert exit_calls == [1]
        mock_logger.error.assert_called()
        assert "APPCIRCLE_ACCESS_TOKEN" in str(mock_logger.error.call_args)

    def test_main_exits_when_excluded_toolsets_invalid(self, monkeypatch):
        """main() logs error and exits with 1 when set_excluded_toolsets raises ValueError."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.setenv("APPCIRCLE_EXCLUDED_TOOLSETS", "invalid_toolset")
        exit_calls = []

        def fake_exit(code):
            exit_calls.append(code)
            raise SystemExit(code)

        with pytest.raises(SystemExit):
            with patch("src.server.sys.exit", side_effect=fake_exit):
                with patch("src.server.logger") as mock_logger:
                    with patch("src.server.settings") as mock_settings:
                        mock_settings.set_excluded_toolsets.side_effect = ValueError("Invalid toolset(s)")
                        import src.server as server_module
                        server_module.main()
        assert exit_calls == [1]
        mock_logger.error.assert_called()
        mock_settings.set_excluded_toolsets.assert_called_once()

    def test_main_configures_settings_and_runs_mcp(self, monkeypatch):
        """main() configures settings, validates, imports tools, and calls mcp.run(transport='stdio')."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.delenv("APPCIRCLE_EXCLUDED_TOOLSETS", raising=False)

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = MagicMock()
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.set_excluded_toolsets.assert_called_once()
        mock_settings.configure.assert_called_once_with(
            access_token="test-token",
            api_url="https://api.appcircle.io",
        )
        mock_settings.validate.assert_called_once()
        mock_mcp.run.assert_called_once_with(transport="stdio")

    def test_main_uses_env_api_url_when_set(self, monkeypatch):
        """main() passes APPCIRCLE_API_URL from env to settings.configure."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://custom.api.example.com")

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = lambda **kwargs: None
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.configure.assert_called_once_with(
            access_token="token",
            api_url="https://custom.api.example.com",
        )

    def test_main_enables_write_tools_by_default(self, monkeypatch):
        """main() calls set_write_tools_enabled(True) when AC_MCP_ENABLE_WRITE_TOOLS is unset (opt-out default)."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.delenv("AC_MCP_ENABLE_WRITE_TOOLS", raising=False)

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = MagicMock()
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.set_write_tools_enabled.assert_called_once_with(True)

    @pytest.mark.parametrize("env_value", ["true", "TRUE", "1", "yes", "on"])
    def test_main_enables_write_tools_from_truthy_env(self, monkeypatch, env_value):
        """main() calls set_write_tools_enabled(True) for various truthy AC_MCP_ENABLE_WRITE_TOOLS values."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.setenv("AC_MCP_ENABLE_WRITE_TOOLS", env_value)

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = MagicMock()
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.set_write_tools_enabled.assert_called_once_with(True)

    def test_main_disables_write_tools_for_unrecognized_env(self, monkeypatch):
        """main() calls set_write_tools_enabled(False) for an unrecognized AC_MCP_ENABLE_WRITE_TOOLS value."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.setenv("AC_MCP_ENABLE_WRITE_TOOLS", "nope")

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = MagicMock()
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.set_write_tools_enabled.assert_called_once_with(False)

    @pytest.mark.parametrize("env_value", ["false", "FALSE", "0", "no", "off"])
    def test_main_disables_write_tools_from_explicit_falsy_env(self, monkeypatch, env_value):
        """main() calls set_write_tools_enabled(False) when explicitly opted out (opt-out path)."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.setenv("AC_MCP_ENABLE_WRITE_TOOLS", env_value)

        with patch("src.server.settings") as mock_settings:
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = MagicMock()
                with patch("src.server.logger"):
                    import src.server as server_module
                    server_module.main()
        mock_settings.set_write_tools_enabled.assert_called_once_with(False)

    def test_main_logs_excluded_toolsets_when_non_empty(self, monkeypatch):
        """main() logs excluded toolsets when EXCLUDED_TOOLSETS is set."""
        monkeypatch.setenv("APPCIRCLE_ACCESS_TOKEN", "token")
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")

        with patch("src.server.settings") as mock_settings:
            mock_settings.EXCLUDED_TOOLSETS = {"build_module", "report"}
            with patch("src.server.mcp") as mock_mcp:
                mock_mcp.run = lambda **kwargs: None
                with patch("src.server.logger") as mock_logger:
                    import src.server as server_module
                    server_module.main()
        # Should have logged excluded toolsets (e.g. "Excluded toolsets: ['build_module', 'report']")
        log_calls = [str(c) for c in mock_logger.info.call_args_list]
        assert any("excluded" in c.lower() or "build_module" in c or "report" in c for c in log_calls)

    def test_http_does_not_require_access_token(self, monkeypatch):
        """With --transport streamable-http, main() does not require APPCIRCLE_ACCESS_TOKEN."""
        monkeypatch.delenv("APPCIRCLE_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("APPCIRCLE_API_URL", "https://api.appcircle.io")
        monkeypatch.setattr("sys.argv", ["appcircle-mcp", "--transport", "streamable-http"])

        with patch("src.server._run_http") as mock_run_http:
            with patch("src.server.logger"):
                import src.server as server_module
                server_module.main()
        mock_run_http.assert_called_once_with("127.0.0.1", 8000)

    def test_http_rejects_request_without_auth_header(self):
        """Middleware returns 401 for requests without Authorization Bearer header."""
        from starlette.testclient import TestClient

        from src.mcp_instance import mcp
        from src.server import TokenExtractionMiddleware

        mcp.settings.streamable_http_path = "/"
        app = mcp.streamable_http_app()
        app.add_middleware(TokenExtractionMiddleware)
        client = TestClient(app)
        response = client.post("/")
        assert response.status_code == 401
        assert "error" in response.json() or "Missing" in response.text

    def test_middleware_allows_health_without_auth(self):
        """GET /health succeeds without Authorization header."""
        from starlette.testclient import TestClient

        from src import __version__
        from src.mcp_instance import mcp
        from src.server import TokenExtractionMiddleware

        mcp.settings.streamable_http_path = "/"
        app = mcp.streamable_http_app()
        app.add_middleware(TokenExtractionMiddleware)
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": __version__}

    def test_initialize_server_info_version_matches_package_version(self):
        """MCP initialize reports the package version in serverInfo, not the mcp library version."""
        from starlette.testclient import TestClient

        from src import __version__
        from src.mcp_instance import mcp

        mcp.settings.streamable_http_path = "/"
        with TestClient(mcp.streamable_http_app(), base_url="http://localhost:8000") as client:
            response = client.post(
                "/",
                headers={"Accept": "application/json, text/event-stream"},
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1"},
                    },
                },
            )
        server_info = response.json()["result"]["serverInfo"]
        assert server_info == {**server_info, "name": "Appcircle MCP", "version": __version__}

    def test_health_version_matches_package_metadata(self):
        """GET /health version field is a non-empty string matching the installed package version."""
        from importlib.metadata import version as pkg_version

        from starlette.testclient import TestClient

        from src.mcp_instance import mcp
        from src.server import TokenExtractionMiddleware

        mcp.settings.streamable_http_path = "/"
        app = mcp.streamable_http_app()
        app.add_middleware(TokenExtractionMiddleware)
        client = TestClient(app)
        response = client.get("/health")
        assert response.json()["version"] == pkg_version("appcircle-mcp-server")


class TestTokenVerificationMiddleware:
    """Tests for TokenExtractionMiddleware bearer-token verification."""

    @staticmethod
    def _client():
        """Middleware in front of a route that echoes the context token seen by ApiClient."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.core.auth import get_access_token
        from src.server import TokenExtractionMiddleware

        async def home(request):
            return JSONResponse({"token": get_access_token()})

        app = Starlette(routes=[Route("/", home, methods=["POST"])])
        return TestClient(TokenExtractionMiddleware(app))

    def test_valid_token_passes_and_is_forwarded(self, token_signer):
        """A valid token reaches the app and is the token used for upstream calls."""
        token = token_signer.sign()
        response = self._client().post("/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json() == {"token": token}

    def test_http_issuer_token_passes(self, token_signer):
        """A token whose issuer uses plain http reaches the app."""
        token = token_signer.sign(issuer="http://auth.example.com/auth/realms/appcircle")
        response = self._client().post("/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json() == {"token": token}

    def test_missing_header_returns_401_with_challenge(self, token_signer):
        """No Authorization header -> 401 with WWW-Authenticate: Bearer."""
        response = self._client().post("/")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json() == {"error": "Missing Authorization header"}

    @pytest.mark.parametrize("auth_value", ["Bearer dummytoken", "Bearer ", "Bearer a.b.c"])
    def test_malformed_token_returns_401(self, token_signer, auth_value):
        """Non-JWT bearer values are rejected before reaching the app."""
        response = self._client().post("/", headers={"Authorization": auth_value})
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_wrong_issuer_returns_401(self, token_signer):
        """A token from another realm is rejected."""
        token = token_signer.sign(issuer="https://auth.example.com/auth/realms/other")
        response = self._client().post("/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json() == {"error": "Invalid or expired access token"}

    def test_expired_token_returns_401(self, token_signer):
        """An expired token is rejected."""
        token = token_signer.sign(exp_offset=-60)
        response = self._client().post("/", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json() == {"error": "Invalid or expired access token"}

    def test_mcp_initialize_with_dummy_token_returns_401(self, token_signer):
        """MCP initialize with a non-JWT bearer value ('Bearer dummytoken') is rejected."""
        from starlette.testclient import TestClient

        from src.mcp_instance import mcp
        from src.server import TokenExtractionMiddleware

        mcp.settings.streamable_http_path = "/"
        app = mcp.streamable_http_app()
        app.add_middleware(TokenExtractionMiddleware)
        response = TestClient(app).post(
            "/",
            headers={"Authorization": "Bearer dummytoken"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert response.status_code == 401

    def test_protected_resource_metadata_path_skips_auth(self, token_signer):
        """/.well-known/oauth-protected-resource is not behind auth (no 401)."""
        from starlette.testclient import TestClient

        from src.mcp_instance import mcp
        from src.server import TokenExtractionMiddleware

        mcp.settings.streamable_http_path = "/"
        app = mcp.streamable_http_app()
        app.add_middleware(TokenExtractionMiddleware)
        response = TestClient(app).get("/.well-known/oauth-protected-resource")
        assert response.status_code != 401


class TestRunHttpTransportSecurity:
    """Tests for _run_http transport_security configuration via APPCIRCLE_MCP_ALLOWED_HOST."""

    def test_run_http_sets_transport_security_when_allowed_host_env_set(self, monkeypatch):
        """When APPCIRCLE_MCP_ALLOWED_HOST is set, _run_http configures transport_security with that host."""
        monkeypatch.setenv("APPCIRCLE_MCP_ALLOWED_HOST", "dev-mcp.appcircle.io")
        from src.mcp_instance import mcp
        from src.server import _run_http

        with patch("anyio.run") as mock_anyio_run:
            _run_http("0.0.0.0", 8000)
        mock_anyio_run.assert_called_once()
        assert mcp.settings.transport_security is not None
        assert mcp.settings.transport_security.enable_dns_rebinding_protection is True
        assert mcp.settings.transport_security.allowed_hosts == ["dev-mcp.appcircle.io"]

    def test_run_http_does_not_override_transport_security_when_allowed_host_unset(self, monkeypatch):
        """When APPCIRCLE_MCP_ALLOWED_HOST is not set, _run_http does not override transport_security."""
        monkeypatch.delenv("APPCIRCLE_MCP_ALLOWED_HOST", raising=False)
        from src.mcp_instance import mcp
        from src.server import _run_http

        transport_security_before = mcp.settings.transport_security

        with patch("anyio.run"):
            _run_http("127.0.0.1", 8000)

        # Should still be the same object, not replaced by our code
        assert mcp.settings.transport_security is transport_security_before


class TestParseArgsPort:
    """Tests for port resolution: APPCIRCLE_MCP_PORT env var and --port CLI precedence."""

    def test_port_env_var_used_when_no_cli_port(self, monkeypatch):
        """APPCIRCLE_MCP_PORT sets the port when --port is not provided."""
        monkeypatch.setenv("APPCIRCLE_MCP_PORT", "9000")
        monkeypatch.delenv("APPCIRCLE_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("sys.argv", ["appcircle-mcp", "--transport", "streamable-http"])

        with patch("src.server._run_http") as mock_run_http:
            with patch("src.server.logger"):
                import src.server as server_module
                server_module.main()
        mock_run_http.assert_called_once_with("127.0.0.1", 9000)

    def test_port_cli_takes_precedence_over_env(self, monkeypatch):
        """--port CLI arg takes precedence over APPCIRCLE_MCP_PORT."""
        monkeypatch.setenv("APPCIRCLE_MCP_PORT", "9000")
        monkeypatch.delenv("APPCIRCLE_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("sys.argv", ["appcircle-mcp", "--transport", "streamable-http", "--port", "3000"])

        with patch("src.server._run_http") as mock_run_http:
            with patch("src.server.logger"):
                import src.server as server_module
                server_module.main()
        mock_run_http.assert_called_once_with("127.0.0.1", 3000)

    def test_invalid_port_env_falls_back_to_default(self, monkeypatch):
        """Invalid APPCIRCLE_MCP_PORT falls back to default 8000."""
        monkeypatch.setenv("APPCIRCLE_MCP_PORT", "not-a-number")
        monkeypatch.delenv("APPCIRCLE_ACCESS_TOKEN", raising=False)
        monkeypatch.setattr("sys.argv", ["appcircle-mcp", "--transport", "streamable-http"])

        with patch("src.server._run_http") as mock_run_http:
            with patch("src.server.logger") as mock_logger:
                import src.server as server_module
                server_module.main()
        mock_run_http.assert_called_once_with("127.0.0.1", 8000)
        mock_logger.warning.assert_called()
        assert "APPCIRCLE_MCP_PORT" in str(mock_logger.warning.call_args)
