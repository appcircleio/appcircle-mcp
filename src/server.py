import argparse
import os
import sys

import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .mcp_instance import mcp
from .config.settings import settings, TOOLSETS
from .core.logger import logger
from .core.auth import reset_request_token, set_request_token, verify_access_token

VALID_TRANSPORTS = ("stdio", "streamable-http")
TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
UNAUTHENTICATED_PATHS = frozenset({"/health", "/.well-known/oauth-protected-resource"})


def _unauthorized(message: str) -> JSONResponse:
    """401 response with the WWW-Authenticate challenge required by the MCP auth spec."""
    return JSONResponse(
        {"error": message},
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable (case-insensitive "1"/"true"/"yes"/"on")."""
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in TRUE_ENV_VALUES


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for load balancers and Docker HEALTHCHECK."""
    return JSONResponse({"status": "ok", "version": __version__})


class TokenExtractionMiddleware:
    """ASGI middleware: verify the Authorization Bearer token and put it in context for pass-through auth."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        auth_value = headers.get(b"authorization", b"").decode("utf-8", errors="replace")

        path = scope.get("path", "")
        if path in UNAUTHENTICATED_PATHS:
            await self.app(scope, receive, send)
            return

        if not auth_value.strip().lower().startswith("bearer "):
            await _unauthorized("Missing Authorization header")(scope, receive, send)
            return

        token_value = auth_value.strip()[7:].strip()
        try:
            verify_access_token(token_value)
        except jwt.PyJWTError as e:
            logger.debug(f"Rejected access token: {type(e).__name__}")
            await _unauthorized("Invalid or expired access token")(scope, receive, send)
            return

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
        env_port = os.getenv("APPCIRCLE_MCP_PORT", "").strip()
        if env_port:
            try:
                args.port = int(env_port)
            except ValueError:
                logger.warning(f"Invalid APPCIRCLE_MCP_PORT value: {env_port!r}, using default 8000")
                args.port = 8000
        else:
            args.port = 8000

    excluded = set()
    excluded.update(args.exclude or [])
    if args.exclude_toolsets:
        excluded.update(s.strip() for s in args.exclude_toolsets.split(",") if s.strip())
    env_val = os.getenv("APPCIRCLE_EXCLUDED_TOOLSETS", "").strip()
    if env_val:
        excluded.update(s.strip() for s in env_val.split(",") if s.strip())
    args.excluded = excluded

    args.enable_write_tools = _parse_bool_env("AC_MCP_ENABLE_WRITE_TOOLS", default=True)

    return args


def _run_http(host: str, port: int) -> None:
    """Run the MCP server with Streamable HTTP transport and token middleware."""
    import anyio
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.streamable_http_path = "/"

    allowed_host = os.getenv("APPCIRCLE_MCP_ALLOWED_HOST", "").strip()
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
    args = _parse_args()

    api_url = os.getenv("APPCIRCLE_API_URL") or ""

    if args.transport == "stdio":
        access_token = os.getenv("APPCIRCLE_ACCESS_TOKEN")
        if not access_token:
            logger.error("APPCIRCLE_ACCESS_TOKEN is required for stdio transport")
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
    allowed_host = os.getenv("APPCIRCLE_MCP_ALLOWED_HOST", "").strip()
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
