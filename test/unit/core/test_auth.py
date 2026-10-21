"""Unit tests for auth module: contextvar, get_access_token and verify_access_token."""

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from src.core.auth import (
    get_access_token,
    set_request_token,
    reset_request_token,
    verify_access_token,
)


class TestGetAccessToken:
    """Tests for get_access_token()."""

    def test_get_access_token_prefers_contextvar(self, test_settings):
        """Contextvar token takes precedence over settings."""
        tok = set_request_token("request-token")
        try:
            assert get_access_token() == "request-token"
        finally:
            reset_request_token(tok)

    def test_get_access_token_falls_back_to_settings(self, test_settings):
        """When no contextvar is set, settings token is returned."""
        assert get_access_token() == "test-token-for-unit-tests"

    def test_get_access_token_raises_when_no_token(self):
        """Raises ValueError when neither contextvar nor settings has a token."""
        from src.config.settings import settings

        original = settings.APPCIRCLE_ACCESS_TOKEN
        settings.APPCIRCLE_ACCESS_TOKEN = None
        try:
            with pytest.raises(ValueError, match="No access token available"):
                get_access_token()
        finally:
            settings.APPCIRCLE_ACCESS_TOKEN = original


class TestVerifyAccessToken:
    """Tests for verify_access_token()."""

    @pytest.mark.parametrize(
        "issuer",
        [
            "https://auth.example.com/auth/realms/appcircle",
            "http://auth.example.com/auth/realms/appcircle",
            "https://sso.example.org/realms/appcircle",
            "http://appcircle.example.com:8080/auth/realms/appcircle",
            "https://auth.example.com/auth/realms/appcircle/",
        ],
    )
    def test_valid_token_passes_for_any_host_and_scheme(self, token_signer, issuer):
        """RS256 + kid + future exp + iss ending in /realms/appcircle passes, whatever the host or scheme."""
        verify_access_token(token_signer.sign(issuer=issuer))

    def test_audience_is_not_checked(self, token_signer):
        """Tokens with any aud claim are accepted."""
        verify_access_token(token_signer.sign(aud="some-other-client"))

    def test_no_network_access(self, token_signer, monkeypatch):
        """Verification never opens a network connection."""
        import socket

        def no_network(*args, **kwargs):
            raise AssertionError("network access attempted")

        monkeypatch.setattr(socket, "create_connection", no_network)
        monkeypatch.setattr(socket.socket, "connect", no_network)
        verify_access_token(token_signer.sign())

    @pytest.mark.parametrize("token", ["dummytoken", "a.b.c", "", "e30.e30.sig"])
    def test_malformed_token_rejected(self, token):
        """Non-JWT strings and tokens with empty headers are rejected."""
        with pytest.raises(jwt.PyJWTError):
            verify_access_token(token)

    def test_expired_token_rejected(self, token_signer):
        """A token whose exp is in the past is rejected."""
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_access_token(token_signer.sign(exp_offset=-60))

    def test_missing_exp_rejected(self):
        """A token without an exp claim is rejected."""
        token = jwt.encode(
            {"iss": "https://auth.example.com/auth/realms/appcircle"},
            rsa.generate_private_key(public_exponent=65537, key_size=2048),
            algorithm="RS256",
            headers={"kid": "k"},
        )
        with pytest.raises(jwt.MissingRequiredClaimError):
            verify_access_token(token)

    def test_missing_issuer_rejected(self, token_signer):
        """A token without an iss claim is rejected."""
        with pytest.raises(jwt.MissingRequiredClaimError):
            verify_access_token(token_signer.sign(issuer=None))

    @pytest.mark.parametrize(
        "issuer",
        [
            "https://auth.example.com/auth/realms/other",
            "https://auth.example.com/auth/realms/appcircle-other",
            "http://auth.example.com/auth/realms/other",
            "https://accounts.example.net",
            "appcircle",
        ],
    )
    def test_unexpected_issuer_rejected(self, token_signer, issuer):
        """Issuers for other realms and unrelated issuers are rejected."""
        with pytest.raises(jwt.InvalidIssuerError):
            verify_access_token(token_signer.sign(issuer=issuer))

    def test_non_string_issuer_rejected(self):
        """A hand-crafted token with a non-string iss claim is rejected."""
        import base64
        import json

        def segment(obj):
            return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

        token = ".".join([
            segment({"alg": "RS256", "kid": "test-kid", "typ": "JWT"}),
            segment({"iss": ["https://auth.example.com/auth/realms/appcircle"], "exp": 9999999999}),
            "c2ln",
        ])
        with pytest.raises(jwt.InvalidIssuerError):
            verify_access_token(token)

    def test_missing_kid_rejected(self, token_signer):
        """A token header without a kid is rejected."""
        with pytest.raises(jwt.InvalidTokenError, match="Unexpected token header"):
            verify_access_token(token_signer.sign(kid=None))

    def test_non_rs256_token_rejected(self):
        """Tokens whose header alg is not RS256 (e.g. HS256) are rejected."""
        token = jwt.encode(
            {"iss": "https://auth.example.com/auth/realms/appcircle", "exp": 9999999999},
            "secret-secret-secret-secret-secret!",
            algorithm="HS256",
            headers={"kid": "test-kid"},
        )
        with pytest.raises(jwt.InvalidTokenError, match="Unexpected token header"):
            verify_access_token(token)
