"""
Unit tests for AC_MCP_ENABLE_WRITE_TOOLS gating: write/action tools must not be
registered with the MCP tool manager unless the flag is enabled.

_run_tool_list_with_write_tools() is the reusable harness for this: each write
tool's own test module can call it with enabled=False and enabled=True and
assert the tool's name is absent/present respectively (mirroring
test_tools_excluded_registration.py's toolset-exclusion pattern).
"""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_tool_list_with_write_tools(enabled: bool):
    """Run in subprocess: set ENABLE_WRITE_TOOLS, import tools, print comma-separated tool names."""
    code = f"""
from src.config.settings import settings
settings.configure(access_token="test", api_url="https://api.appcircle.io")
settings.set_write_tools_enabled({enabled!r})
from src.mcp_instance import mcp
from src import tools
names = sorted(mcp._tool_manager._tools.keys())
print(",".join(names))
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=10,
    )
    assert result.returncode == 0, (result.stderr or result.stdout)
    return result.stdout.strip().split(",") if result.stdout.strip() else []


def test_trigger_build_absent_when_write_tools_disabled():
    """trigger_build is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "trigger_build" not in tools_disabled
    # A read tool from the same toolset should still be present.
    assert "get_build_profiles" in tools_disabled


def test_trigger_build_present_when_write_tools_enabled():
    """trigger_build is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "trigger_build" in tools_enabled


def test_cancel_build_absent_when_write_tools_disabled():
    """cancel_build is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "cancel_build" not in tools_disabled


def test_cancel_build_present_when_write_tools_enabled():
    """cancel_build is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "cancel_build" in tools_enabled


def test_start_publish_absent_when_write_tools_disabled():
    """start_publish is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "start_publish" not in tools_disabled


def test_start_publish_present_when_write_tools_enabled():
    """start_publish is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "start_publish" in tools_enabled


def test_stop_publish_absent_when_write_tools_disabled():
    """stop_publish is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "stop_publish" not in tools_disabled


def test_stop_publish_present_when_write_tools_enabled():
    """stop_publish is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "stop_publish" in tools_enabled


def test_update_app_version_release_notes_absent_when_write_tools_disabled():
    """update_app_version_release_notes is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "update_app_version_release_notes" not in tools_disabled


def test_update_app_version_release_notes_present_when_write_tools_enabled():
    """update_app_version_release_notes is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "update_app_version_release_notes" in tools_enabled


def test_send_app_version_to_testers_absent_when_write_tools_disabled():
    """send_app_version_to_testers is not registered when AC_MCP_ENABLE_WRITE_TOOLS is disabled."""
    tools_disabled = _run_tool_list_with_write_tools(False)

    assert "send_app_version_to_testers" not in tools_disabled


def test_send_app_version_to_testers_present_when_write_tools_enabled():
    """send_app_version_to_testers is registered when AC_MCP_ENABLE_WRITE_TOOLS is enabled."""
    tools_enabled = _run_tool_list_with_write_tools(True)

    assert "send_app_version_to_testers" in tools_enabled
