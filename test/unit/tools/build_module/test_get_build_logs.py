"""Unit tests for get_build_logs: tail truncation, full_log, step scoping, grep, and errors."""

import pytest
from httpx import Response

import src.tools.build_module.get_build_logs as get_build_logs_module
from src.tools.build_module.get_build_logs import get_build_logs

COMMIT_ID = "aaaaaaaa-0001-0000-0000-000000000001"
BUILD_ID = "aaaaaaaa-0002-0000-0000-000000000002"
LOG_PATH = f"/build/v2/commits/{COMMIT_ID}/builds/{BUILD_ID}/logs"

SAMPLE_LOG_LINES = [
    "@@[section:begin] 12/25/2025 11:59:53 Starting workflow",
    "Agent Version: 1.8.4",
    "@@[section:end] Starting workflow",
    "@@[section:begin] 12/25/2025 11:59:53 Step started: Git Clone",
    "Cloning repository...",
    "Clone complete.",
    "@@[section:end] 12/25/2025 11:59:55 Step completed: Git Clone, Ver: 1.1.1",
    "@@[section:begin] 12/25/2025 11:59:55 Step started: Custom Script(1)",
    "Running script 1",
    "@@[section:end] 12/25/2025 11:59:55 Step completed: Custom Script(1), Ver: 1.0.3",
    "@@[section:begin] 12/25/2025 11:59:56 Step started: Custom Script(2)",
    "Running script 2",
    "ERROR: something failed",
    "@@[section:end] 12/25/2025 11:59:57 Step completed: Custom Script(2), Ver: 1.0.3",
    "@@[section:begin] 12/25/2025 12:00:00 Step started: Xcode Select",
    "Selecting Xcode 16.2",
    "@@[section:end] 12/25/2025 12:00:00 Step completed: Xcode Select",
]
SAMPLE_LOG_TEXT = "\n".join(SAMPLE_LOG_LINES)


def _mock_log(mocked_api, text=SAMPLE_LOG_TEXT, status_code=200):
    mocked_api.get(LOG_PATH).mock(
        return_value=Response(status_code, text=text, headers={"Content-Type": "text/plain"})
    )


@pytest.mark.asyncio
async def test_get_build_logs_default_tail(mocked_api):
    """Default (no params) returns the tail of the log and reports steps found."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_TEXT  # whole log fits well under 200 lines / 64KB
    assert result["meta"]["total_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["returned_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["truncated"] is False
    assert result["meta"]["full_log"] is False
    assert result["meta"]["step"] is None
    assert result["meta"]["steps"] == ["Git Clone", "Custom Script(1)", "Custom Script(2)", "Xcode Select"]


@pytest.mark.asyncio
async def test_get_build_logs_tail_lines_param(mocked_api):
    """tail_lines limits the result to the last N lines of the (scoped) log."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, tail_lines=3)

    assert result["success"] is True
    assert result["data"].splitlines() == SAMPLE_LOG_LINES[-3:]
    assert result["meta"]["returned_lines"] == 3
    assert result["meta"]["total_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_build_logs_tail_lines_capped_at_max(mocked_api):
    """tail_lines above 1000 is capped at 1000."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, tail_lines=5000)

    assert result["success"] is True
    # Log is shorter than 1000 lines, so nothing is actually cut despite the request.
    assert result["meta"]["returned_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_build_logs_full_log_returns_everything(mocked_api):
    """full_log=True bypasses the default tail truncation."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, full_log=True)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_TEXT
    assert result["meta"]["full_log"] is True
    assert result["meta"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_build_logs_step_scoping_disambiguates_duplicate_names(mocked_api):
    """step scopes output to one block, exact-matching the "(N)" suffix used for duplicates."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, step="Custom Script(2)")

    assert result["success"] is True
    assert result["meta"]["step"] == "Custom Script(2)"
    assert "Running script 2" in result["data"]
    assert "Running script 1" not in result["data"]
    assert "Step started: Custom Script(2)" in result["data"]
    assert "Step completed: Custom Script(2), Ver: 1.0.3" in result["data"]


@pytest.mark.asyncio
async def test_get_build_logs_step_scoping_case_insensitive(mocked_api):
    """step matching is case-insensitive."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, step="xcode select")

    assert result["success"] is True
    assert result["meta"]["step"] == "Xcode Select"
    assert "Selecting Xcode 16.2" in result["data"]


@pytest.mark.asyncio
async def test_get_build_logs_step_not_found_lists_available_steps(mocked_api):
    """When step doesn't match anything, returns validation_error with available steps."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, step="Nonexistent Step")

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_logs"
    assert result["error"]["type"] == "validation_error"
    assert result["error"]["details"]["requested_step"] == "Nonexistent Step"
    assert result["error"]["details"]["available_steps"] == [
        "Git Clone",
        "Custom Script(1)",
        "Custom Script(2)",
        "Xcode Select",
    ]


@pytest.mark.asyncio
async def test_get_build_logs_grep_filters_before_truncation(mocked_api):
    """grep keeps only matching lines (case-insensitive substring), reflected in total_lines."""
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, grep="error")

    assert result["success"] is True
    assert result["data"] == "ERROR: something failed"
    assert result["meta"]["total_lines"] == 1
    assert result["meta"]["returned_lines"] == 1
    assert result["meta"]["grep"] == "error"
    assert result["meta"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_build_logs_grep_combined_with_step(mocked_api):
    """grep applies within the step-scoped lines, not the whole log."""
    _mock_log(mocked_api)

    result = await get_build_logs(
        commit_id=COMMIT_ID, build_id=BUILD_ID, step="Custom Script(2)", grep="running"
    )

    assert result["success"] is True
    assert result["data"] == "Running script 2"


@pytest.mark.asyncio
async def test_get_build_logs_byte_cap_truncates_tail_mode(mocked_api, monkeypatch):
    """A small DEFAULT_MAX_BYTES still keeps the most recent lines and flags truncated."""
    monkeypatch.setattr(get_build_logs_module, "DEFAULT_MAX_BYTES", 70)
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, tail_lines=2)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_LINES[-1]
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_build_logs_byte_cap_applies_to_full_log(mocked_api, monkeypatch):
    """full_log=True still respects the (higher) safety byte cap."""
    monkeypatch.setattr(get_build_logs_module, "FULL_LOG_MAX_BYTES", 70)
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, full_log=True)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_LINES[-1]
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_build_logs_byte_cap_truncates_within_single_oversized_line(mocked_api, monkeypatch):
    """If even the single remaining line exceeds the cap, keep the tail bytes of that line."""
    monkeypatch.setattr(get_build_logs_module, "DEFAULT_MAX_BYTES", 20)
    _mock_log(mocked_api)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID, tail_lines=1)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_LINES[-1][-20:]
    assert len(result["data"].encode("utf-8")) == 20
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_build_logs_no_steps_found(mocked_api):
    """A log with no step markers still works; steps is an empty list."""
    _mock_log(mocked_api, text="just some plain output\nwith no step markers")

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is True
    assert result["meta"]["steps"] == []


@pytest.mark.asyncio
async def test_get_build_logs_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    _mock_log(mocked_api, text="Internal server error", status_code=500)

    result = await get_build_logs(commit_id=COMMIT_ID, build_id=BUILD_ID)

    assert result["success"] is False
    assert result["error"]["tool"] == "get_build_logs"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
