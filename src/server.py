import argparse
import os
import sys

from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .mcp_instance import mcp
from .config.settings import settings, TOOLSETS
from .core.logger import logger
from .core.auth import set_request_token, reset_request_token

VALID_TRANSPORTS = ("stdio", "streamable-http")
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}


def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable (case-insensitive "1"/"true"/"yes"/"on")."""
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in TRUE_ENV_VALUES


def _bootstrap_hosted_config() -> None:
    """Resolves this process's env through Appcircle ConfigService (BE-8827) when running as
    Appcircle's own hosted deployment (mcp.appcircle.io) - a no-op for every local/customer
    install. Those installs never set AC_CONFIG_SERVICE_URL and never install the optional
    "hosted" extra (`appcircle-config-client` lives on the private Nexus registry, unreachable
    from a customer's own `pip install .` - see docs/tasks/BE-8827/spec.md), so this function
    returns immediately without even attempting the import.

    Must run before _parse_args()/the rest of main() reads any of the env vars below, so the
    resolved values are in os.environ by the time those functions run - they all read
    os.getenv(...) from inside a function body, not at module-import time, so this ordering is
    sufficient. The one exception is core.logger's LOG_LEVEL read, which happens at module-import
    time (`from .core.logger import logger` at the top of this file, evaluated before main() ever
    runs) and is not deferrable without restructuring this module's own top-level
    @mcp.custom_route/TokenExtractionMiddleware definitions - accepted as a known, low-stakes
    limitation (the logger falls back to its own default, nothing functional breaks).
    """
    service_url = os.getenv("AC_CONFIG_SERVICE_URL", "").strip()
    if not service_url:
        return

    try:
        import appcircle_config_client as config_client
    except ImportError as error:
        logger.error(
            "AC_CONFIG_SERVICE_URL is set but appcircle-config-client is not installed - "
            "install the 'hosted' extra: pip install '.[hosted]'"
        )
        raise SystemExit(1) from error

    import anyio

    async def _resolve() -> None:
        await config_client.bootstrap(
            service_url=service_url,
            def_path="envdef.yaml",
            credential_source=os.getenv("AC_CONFIG_CREDENTIAL_SOURCE"),
        )

    try:
        anyio.run(_resolve)
    except config_client.ConfigClientError as error:
        logger.error(f"Config service resolve failed: {error}")
        raise SystemExit(1) from error


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and Docker HEALTHCHECK."""
    return JSONResponse({"status": "ok", "version": __version__})


class TokenExtractionMiddleware:
    """ASGI middleware: extract Authorization Bearer token into context for pass-through auth."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode("utf-8", errors="replace")

        path = scope.get("path", "")
        if path == "/health":
            await self.app(scope, receive, send)
            return

        if not auth_value.strip().lower().startswith("bearer "):
            response = JSONResponse(
                {"error": "Missing Authorization header"},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        token_value = auth_value[7:].strip()
        tok = set_request_token(token_value)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_token(tok)


def _parse_excluded_toolsets(argv: list[str] | None = None) -> set:
    """Parse CLI and env for excluded toolsets only. Backward-compatible helper."""
    return _parse_args(argv).excluded


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI for excluded toolsets, transport, host, and port."""
    parser = argparse.ArgumentParser(description="Appcircle MCP Server")
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        metavar="TOOLSET",
        help="Toolsets to exclude (e.g. build_module report)",
    )
    parser.add_argument(
        "--exclude-toolsets",
        type=str,
        default="",
        metavar="LIST",
        help="Comma-separated toolsets to exclude (e.g. build_module,report)",
    )
    parser.add_argument(
        "--transport",
        choices=VALID_TRANSPORTS,
        default="stdio",
        help="Transport: stdio (default, local) or streamable-http (remote HTTP).",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Bind host (streamable-http only). Default: 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port (streamable-http only). Default: 8000.",
    )
    parser.epilog = f"Valid toolsets: {sorted(TOOLSETS)}."
    args, _ = parser.parse_known_args(argv)

    if args.port is None:
        # AC_PORT is the new name (BE-8827); APPCIRCLE_MCP_PORT is kept as a fallback so a
        # customer's existing local config keeps working unchanged.
        port_var = "AC_PORT" if os.getenv("AC_PORT") else "APPCIRCLE_MCP_PORT"
        env_port = (os.getenv("AC_PORT") or os.getenv("APPCIRCLE_MCP_PORT") or "").strip()
        if env_port:
            try:
                args.port = int(env_port)
            except ValueError:
                logger.warning(f"Invalid {port_var} value: {env_port!r}, using default 8000")
                args.port = 8000
        else:
            args.port = 8000

    excluded = set()
    excluded.update(args.exclude or [])
    if args.exclude_toolsets:
        excluded.update(s.strip() for s in args.exclude_toolsets.split(",") if s.strip())
    # AC_EXCLUDED_TOOLSETS is the new name; APPCIRCLE_EXCLUDED_TOOLSETS is kept as a fallback.
    env_val = (os.getenv("AC_EXCLUDED_TOOLSETS") or os.getenv("APPCIRCLE_EXCLUDED_TOOLSETS") or "").strip()
    if env_val:
        excluded.update(s.strip() for s in env_val.split(",") if s.strip())
    args.excluded = excluded

    # AC_WRITE_TOOLS_ENABLED is the new name; AC_MCP_ENABLE_WRITE_TOOLS (itself already AC_-prefixed,
    # just with a redundant own-service "MCP" component - see environment-variables.md's component
    # rule) is kept as a fallback so a customer's existing local config keeps working unchanged.
    args.enable_write_tools = _parse_bool_env(
        "AC_WRITE_TOOLS_ENABLED", default=_parse_bool_env("AC_MCP_ENABLE_WRITE_TOOLS", default=True)
    )

    return args


def _run_http(host: str, port: int) -> None:
    """Run the MCP server with Streamable HTTP transport and token middleware."""
    import anyio
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = "/"

    # AC_ALLOWED_HOST is the new name; APPCIRCLE_MCP_ALLOWED_HOST is kept as a fallback.
    allowed_host = (os.getenv("AC_ALLOWED_HOST") or os.getenv("APPCIRCLE_MCP_ALLOWED_HOST") or "").strip()
    if allowed_host:
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[allowed_host],
        )

    starlette_app = mcp.streamable_http_app()
    starlette_app.add_middleware(TokenExtractionMiddleware)

    config = uvicorn.Config(starlette_app, host=host, port=port)
    server = uvicorn.Server(config)
    anyio.run(server.serve)


def main():
    """Main entry point for the MCP server."""
    _bootstrap_hosted_config()

    args = _parse_args()

    # AC_API_EXTERNAL_URL is the new name (BE-8827); APPCIRCLE_API_URL is kept as a fallback so
    # a customer's existing local config keeps working unchanged.
    api_url = os.getenv("AC_API_EXTERNAL_URL") or os.getenv("APPCIRCLE_API_URL") or ""

    if args.transport == "stdio":
        # AC_API_ACCESS_TOKEN is the new name; APPCIRCLE_ACCESS_TOKEN is kept as a fallback, same
        # reasoning as AC_API_EXTERNAL_URL above.
        access_token = os.getenv("AC_API_ACCESS_TOKEN") or os.getenv("APPCIRCLE_ACCESS_TOKEN")
        if not access_token:
            logger.error("AC_API_ACCESS_TOKEN (or APPCIRCLE_ACCESS_TOKEN) is required for stdio transport")
            sys.exit(1)
        settings.configure(access_token=access_token, api_url=api_url)
        settings.validate()
    else:
        settings.configure(access_token="", api_url=api_url)

    try:
        settings.set_excluded_toolsets(args.excluded)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    settings.set_write_tools_enabled(args.enable_write_tools)

    logger.info("Appcircle MCP Server starting...")
    logger.info(f"API URL: {settings.APPCIRCLE_API_URL}")
    if settings.EXCLUDED_TOOLSETS:
        logger.info(f"Excluded toolsets: {sorted(settings.EXCLUDED_TOOLSETS)}")
    logger.info(f"Write tools enabled: {settings.ENABLE_WRITE_TOOLS}")
    allowed_host = (os.getenv("AC_ALLOWED_HOST") or os.getenv("APPCIRCLE_MCP_ALLOWED_HOST") or "").strip()
    if args.transport != "stdio" and allowed_host:
        logger.info(f"Allowed Host (streamable-http): {allowed_host}")

    from . import tools

    logger.info("All tools registered successfully")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        _run_http(args.host, args.port)


if __name__ == "__main__":
    main()
