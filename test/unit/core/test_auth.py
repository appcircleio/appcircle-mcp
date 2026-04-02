"""Unit tests for auth module: contextvar and get_access_token."""

import pytest

from src.core.auth import (
    get_access_token,
    set_request_token,
    reset_request_token,
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
