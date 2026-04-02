"""Per-request access token for HTTP (pass-through auth). Stdio uses settings fallback."""
import contextvars

from ..config.settings import settings

_request_access_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_access_token", default=None
)


def set_request_token(token: str | None) -> contextvars.Token:
    """Set the access token for the current request context. Returns token for reset."""
    return _request_access_token.set(token)


def reset_request_token(token: contextvars.Token) -> None:
    """Reset the request token to the previous value."""
    _request_access_token.reset(token)


def get_access_token() -> str:
    """Return the current request's token (HTTP) or the global token (stdio)."""
    token = _request_access_token.get()
    if token:
        return token
    if settings.APPCIRCLE_ACCESS_TOKEN:
        return settings.APPCIRCLE_ACCESS_TOKEN
    raise ValueError("No access token available")
