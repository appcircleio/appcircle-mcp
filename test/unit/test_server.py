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

    def test_middleware_accepts_bearer_token(self):
        """Middleware passes through when Authorization: Bearer is present."""
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        from src.server import TokenExtractionMiddleware

        async def home(request):
            return JSONResponse({"ok": True})

        app = Starlette(routes=[Route("/", home, methods=["POST"])])
        app = TokenExtractionMiddleware(app)
        client = TestClient(app)
        response = client.post("/", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        assert response.json() == {"ok": True}


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


class TestBootstrapHostedConfig:
    """Tests for _bootstrap_hosted_config() - BE-8827's Config Service integration, only active
    for Appcircle's own hosted deployment, never for a customer's local/self-hosted install."""

    def test_noop_when_service_url_unset(self, monkeypatch):
        """No AC_CONFIG_SERVICE_URL - the default for every local/customer install - means this
        never even attempts the appcircle_config_client import."""
        monkeypatch.delenv("AC_CONFIG_SERVICE_URL", raising=False)

        import src.server as server_module

        # Would raise ModuleNotFoundError if it tried to import (the package isn't installed in
        # this dev environment - it's an optional "hosted" extra, deliberately not a dev dependency
        # either, to keep the test environment matching a real customer install).
        server_module._bootstrap_hosted_config()

    def test_exits_with_clear_message_when_extra_not_installed(self, monkeypatch):
        """AC_CONFIG_SERVICE_URL set but the optional 'hosted' extra isn't installed - a
        misconfigured hosted deployment, not a customer scenario - fails loudly."""
        monkeypatch.setenv("AC_CONFIG_SERVICE_URL", "http://ac-config/v1/config/resolve")

        import src.server as server_module

        with patch("src.server.logger") as mock_logger:
            with pytest.raises(SystemExit) as exc_info:
                server_module._bootstrap_hosted_config()

        assert exc_info.value.code == 1
        mock_logger.error.assert_called_once()
        assert "hosted" in str(mock_logger.error.call_args)

    def test_calls_bootstrap_with_service_url_and_credential_source(self, monkeypatch):
        """When the optional dependency is available, resolves via anyio.run and passes through
        AC_CONFIG_SERVICE_URL / AC_CONFIG_CREDENTIAL_SOURCE."""
        import sys
        import types

        monkeypatch.setenv("AC_CONFIG_SERVICE_URL", "http://ac-config/v1/config/resolve")
        monkeypatch.setenv("AC_CONFIG_CREDENTIAL_SOURCE", "/var/run/secrets/token")

        calls = []

        async def fake_bootstrap(**kwargs):
            calls.append(kwargs)

        class FakeConfigClientError(Exception):
            pass

        fake_module = types.ModuleType("appcircle_config_client")
        fake_module.bootstrap = fake_bootstrap
        fake_module.ConfigClientError = FakeConfigClientError
        monkeypatch.setitem(sys.modules, "appcircle_config_client", fake_module)

        import src.server as server_module

        server_module._bootstrap_hosted_config()

        assert calls == [
            {
                "service_url": "http://ac-config/v1/config/resolve",
                "def_path": "envdef.yaml",
                "credential_source": "/var/run/secrets/token",
            }
        ]

    def test_exits_with_clear_message_on_config_client_error(self, monkeypatch):
        """A resolve failure (ConfigClientError) is logged and turned into a fatal exit, not an
        unhandled traceback."""
        import sys
        import types

        monkeypatch.setenv("AC_CONFIG_SERVICE_URL", "http://ac-config/v1/config/resolve")

        class FakeConfigClientError(Exception):
            pass

        async def failing_bootstrap(**kwargs):
            raise FakeConfigClientError("unreachable")

        fake_module = types.ModuleType("appcircle_config_client")
        fake_module.bootstrap = failing_bootstrap
        fake_module.ConfigClientError = FakeConfigClientError
        monkeypatch.setitem(sys.modules, "appcircle_config_client", fake_module)

        import src.server as server_module

        with patch("src.server.logger") as mock_logger:
            with pytest.raises(SystemExit) as exc_info:
                server_module._bootstrap_hosted_config()

        assert exc_info.value.code == 1
        mock_logger.error.assert_called_once()
        assert "unreachable" in str(mock_logger.error.call_args)
