"""Unit tests that excluded toolsets result in fewer tools registered."""

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_tool_list_with_excluded(excluded: list[str]):
    """Run in subprocess: set excluded toolsets, import tools, print comma-separated tool names."""
    code = f"""
from src.config.settings import settings
settings.configure(access_token="test", api_url="https://api.appcircle.io")
settings.set_excluded_toolsets({excluded!r})
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


def test_excluding_report_omits_report_tools():
    """When report toolset is excluded, no report tools are registered."""
    tools_all = _run_tool_list_with_excluded([])
    tools_no_report = _run_tool_list_with_excluded(["report"])

    report_tools = [t for t in tools_all if "report" in t.lower()]
    assert len(report_tools) > 0, "sanity: there should be some report tools when none excluded"
    for name in report_tools:
        assert name not in tools_no_report, f"report tool {name} should not be registered when report excluded"

    # Build tool should still be present
    assert "get_build_profiles" in tools_no_report


def test_excluding_build_omits_build_tools():
    """When build_module toolset is excluded, no build tools are registered."""
    tools_no_build = _run_tool_list_with_excluded(["build_module"])

    build_tools = ["get_build_profiles", "get_build_profile_details", "get_workflow_detail"]
    for name in build_tools:
        assert name not in tools_no_build, f"build tool {name} should not be registered when build_module excluded"

    # At least one non-build tool should remain
    assert len(tools_no_build) > 0


def test_excluding_all_toolsets_registers_no_tools():
    """Excluding every toolset results in no tools registered."""
    from src.config.settings import TOOLSETS

    tools_none = _run_tool_list_with_excluded(list(TOOLSETS))
    assert tools_none == [], "excluding all toolsets should register no tools"
