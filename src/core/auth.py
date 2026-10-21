"""Per-request access token for HTTP (pass-through auth). Stdio uses settings fallback."""
import contextvars

import jwt

from ..config.settings import settings

_request_access_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_access_token", default=None
)

APPCIRCLE_REALM_SUFFIX = "/realms/appcircle"


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


def verify_access_token(token: str) -> None:
    """
    Check that a bearer token is a well-formed, unexpired Appcircle access token:
    an RS256 header with a kid, a future exp, and an iss ending in
    /realms/appcircle. Raises jwt.PyJWTError if any check fails.

    Shape/expiry pre-check only, the signature is not verified; the Appcircle
    API is the auth boundary.
    """
    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise jwt.InvalidTokenError("Unexpected token header")

    claims = jwt.decode(
        token,
        options={"verify_signature": False, "verify_exp": True, "require": ["exp", "iss"]},
    )
    issuer = claims["iss"]
    if not (isinstance(issuer, str) and issuer.rstrip("/").endswith(APPCIRCLE_REALM_SUFFIX)):
        raise jwt.InvalidIssuerError("Unexpected token issuer")
