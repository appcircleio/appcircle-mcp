"""Unit tests for toolsets: parsing excluded toolsets and settings validation."""

import os

import pytest

from src.config.settings import TOOLSETS, Settings, settings
from src.server import _parse_excluded_toolsets


class TestParseExcludedToolsets:
    """Tests for _parse_excluded_toolsets (CLI and env)."""

    def test_no_args_no_env_returns_empty(self):
        assert _parse_excluded_toolsets(argv=["appcircle-mcp"]) == set()

    def test_exclude_single(self):
        assert _parse_excluded_toolsets(
            argv=["appcircle-mcp", "--exclude", "build_module"]
        ) == {"build_module"}

    def test_exclude_multiple(self):
        assert _parse_excluded_toolsets(
            argv=["appcircle-mcp", "--exclude", "build_module", "report"]
        ) == {"build_module", "report"}

    def test_exclude_toolsets_comma_separated(self):
        assert _parse_excluded_toolsets(
            argv=["appcircle-mcp", "--exclude-toolsets", "build_module,report"]
        ) == {"build_module", "report"}

    def test_exclude_toolsets_with_spaces(self):
        assert _parse_excluded_toolsets(
            argv=["appcircle-mcp", "--exclude-toolsets", " build_module , report "]
        ) == {"build_module", "report"}

    def test_exclude_and_exclude_toolsets_merged(self):
        assert _parse_excluded_toolsets(
            argv=[
                "appcircle-mcp",
                "--exclude", "build_module",
                "--exclude-toolsets", "report,signing_identities",
            ]
        ) == {"build_module", "report", "signing_identities"}

    def test_env_merged_with_argv(self, monkeypatch):
        monkeypatch.setenv("APPCIRCLE_EXCLUDED_TOOLSETS", "enterprise_app_store")
        result = _parse_excluded_toolsets(argv=["appcircle-mcp", "--exclude", "report"])
        assert result == {"report", "enterprise_app_store"}

    def test_env_only(self, monkeypatch):
        monkeypatch.setenv("APPCIRCLE_EXCLUDED_TOOLSETS", "build_module,report")
        result = _parse_excluded_toolsets(argv=["appcircle-mcp"])
        assert result == {"build_module", "report"}

    def test_parse_known_args_ignores_unknown(self):
        # MCP clients might pass extra args; parse_known_args avoids breaking
        result = _parse_excluded_toolsets(
            argv=["appcircle-mcp", "--exclude", "build_module", "--unknown", "x"]
        )
        assert result == {"build_module"}


class TestSetExcludedToolsets:
    """Tests for settings.set_excluded_toolsets validation."""

    def setup_method(self):
        # Reset class attribute (avoid setting instance attr on settings singleton)
        Settings.EXCLUDED_TOOLSETS = set()

    def test_valid_single(self):
        settings.set_excluded_toolsets(["build_module"])
        assert settings.EXCLUDED_TOOLSETS == {"build_module"}

    def test_valid_multiple(self):
        settings.set_excluded_toolsets(["build_module", "report", "signing_identities"])
        assert settings.EXCLUDED_TOOLSETS == {"build_module", "report", "signing_identities"}

    def test_empty_iterable(self):
        settings.set_excluded_toolsets([])
        assert settings.EXCLUDED_TOOLSETS == set()

    def test_strips_whitespace(self):
        settings.set_excluded_toolsets(["  build_module  ", " report "])
        assert settings.EXCLUDED_TOOLSETS == {"build_module", "report"}

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            settings.set_excluded_toolsets(["build_module", "invalid_toolset"])
        assert "Invalid toolset(s)" in str(exc_info.value)
        assert "invalid_toolset" in str(exc_info.value)
        assert "Valid toolsets" in str(exc_info.value)
        for t in TOOLSETS:
            assert t in str(exc_info.value)

    def test_all_valid_toolsets_accepted(self):
        settings.set_excluded_toolsets(TOOLSETS)
        assert settings.EXCLUDED_TOOLSETS == set(TOOLSETS)
