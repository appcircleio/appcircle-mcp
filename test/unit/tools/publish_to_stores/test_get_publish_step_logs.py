"""Unit tests for get_publish_step_logs: tail truncation, full_log, step scoping, grep, and errors."""

import pytest
from httpx import Response

import src.tools.publish_to_stores.get_publish_step_logs as get_publish_step_logs_module
from src.tools.publish_to_stores.get_publish_step_logs import get_publish_step_logs

PLATFORM_TYPE = "ios"
PROFILE_ID = "aaaaaaaa-0001-0000-0000-000000000001"
PUBLISH_ID = "aaaaaaaa-0002-0000-0000-000000000002"
STEP_ID = "aaaaaaaa-0003-0000-0000-000000000003"
LOG_PATH = f"/publish/v2/profiles/{PLATFORM_TYPE}/{PROFILE_ID}/publish/{PUBLISH_ID}/step/{STEP_ID}/logs"

SAMPLE_LOG_LINES = [
    "@@[section:begin] 12/15/2025 13:41:45 Starting workflow",
    "Agent Version: 1.8.4",
    "@@[section:end] Starting workflow",
    "@@[section:begin] 12/15/2025 13:41:45 Step started: Send to Microsoft Intune",
    "Uploading file to Azure Storage...",
    "App published successfully",
    "@@[section:end] 12/15/2025 13:42:13 Step completed: Send to Microsoft Intune, Ver: 2.0.3",
    "@@[section:begin] 12/15/2025 13:42:13 Step started: Export Publish Artifacts",
    "starting to upload files...",
    "ERROR: something failed",
    "@@[section:end] 12/15/2025 13:42:26 Step completed: Export Publish Artifacts, Ver: 1.0.9",
    "@@[section:begin] 12/15/2025 13:42:27 Step started: Completing workflow",
    "@@[section:end] 12/15/2025 13:42:27 Step completed: Completing workflow",
]
SAMPLE_LOG_TEXT = "\n".join(SAMPLE_LOG_LINES)


def _mock_log(mocked_api, text=SAMPLE_LOG_TEXT, status_code=200):
    mocked_api.get(LOG_PATH).mock(
        return_value=Response(status_code, text=text, headers={"Content-Type": "text/plain"})
    )


def _call(**kwargs):
    return get_publish_step_logs(
        platform_type=PLATFORM_TYPE, profile_id=PROFILE_ID, publish_id=PUBLISH_ID, step_id=STEP_ID, **kwargs
    )


@pytest.mark.asyncio
async def test_get_publish_step_logs_default_tail(mocked_api):
    """Default (no params) returns the tail of the log and reports steps found."""
    _mock_log(mocked_api)

    result = await _call()

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_TEXT  # whole log fits well under 200 lines / 64KB
    assert result["meta"]["total_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["returned_lines"] == len(SAMPLE_LOG_LINES)
    assert result["meta"]["truncated"] is False
    assert result["meta"]["full_log"] is False
    assert result["meta"]["step"] is None
    assert result["meta"]["steps"] == [
        "Send to Microsoft Intune",
        "Export Publish Artifacts",
        "Completing workflow",
    ]


@pytest.mark.asyncio
async def test_get_publish_step_logs_tail_lines_param(mocked_api):
    """tail_lines limits the result to the last N lines of the (scoped) log."""
    _mock_log(mocked_api)

    result = await _call(tail_lines=3)

    assert result["success"] is True
    assert result["data"].splitlines() == SAMPLE_LOG_LINES[-3:]
    assert result["meta"]["returned_lines"] == 3
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_publish_step_logs_full_log_returns_everything(mocked_api):
    """full_log=True bypasses the default tail truncation."""
    _mock_log(mocked_api)

    result = await _call(full_log=True)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_TEXT
    assert result["meta"]["full_log"] is True
    assert result["meta"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_publish_step_logs_step_scoping(mocked_api):
    """step scopes output to that step's block, even though the raw log spans multiple steps."""
    _mock_log(mocked_api)

    result = await _call(step="Export Publish Artifacts")

    assert result["success"] is True
    assert result["meta"]["step"] == "Export Publish Artifacts"
    assert "starting to upload files" in result["data"]
    assert "App published successfully" not in result["data"]


@pytest.mark.asyncio
async def test_get_publish_step_logs_step_scoping_case_insensitive(mocked_api):
    """step matching is case-insensitive."""
    _mock_log(mocked_api)

    result = await _call(step="completing workflow")

    assert result["success"] is True
    assert result["meta"]["step"] == "Completing workflow"


@pytest.mark.asyncio
async def test_get_publish_step_logs_step_not_found_lists_available_steps(mocked_api):
    """When step doesn't match anything, returns validation_error with available steps."""
    _mock_log(mocked_api)

    result = await _call(step="Nonexistent Step")

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_step_logs"
    assert result["error"]["type"] == "validation_error"
    assert result["error"]["details"]["requested_step"] == "Nonexistent Step"
    assert result["error"]["details"]["available_steps"] == [
        "Send to Microsoft Intune",
        "Export Publish Artifacts",
        "Completing workflow",
    ]


@pytest.mark.asyncio
async def test_get_publish_step_logs_grep_filters_before_truncation(mocked_api):
    """grep keeps only matching lines (case-insensitive substring), reflected in total_lines."""
    _mock_log(mocked_api)

    result = await _call(grep="error")

    assert result["success"] is True
    assert result["data"] == "ERROR: something failed"
    assert result["meta"]["total_lines"] == 1
    assert result["meta"]["returned_lines"] == 1
    assert result["meta"]["grep"] == "error"
    assert result["meta"]["truncated"] is False


@pytest.mark.asyncio
async def test_get_publish_step_logs_byte_cap_truncates_tail_mode(mocked_api, monkeypatch):
    """A small DEFAULT_MAX_BYTES still keeps the most recent lines and flags truncated."""
    monkeypatch.setattr(get_publish_step_logs_module, "DEFAULT_MAX_BYTES", 100)
    _mock_log(mocked_api)

    result = await _call(tail_lines=2)

    assert result["success"] is True
    assert result["data"] == SAMPLE_LOG_LINES[-1]
    assert result["meta"]["truncated"] is True


@pytest.mark.asyncio
async def test_get_publish_step_logs_no_steps_found(mocked_api):
    """A log with no step markers still works; steps is an empty list."""
    _mock_log(mocked_api, text="just some plain output\nwith no step markers")

    result = await _call()

    assert result["success"] is True
    assert result["meta"]["steps"] == []


@pytest.mark.asyncio
async def test_get_publish_step_logs_error_returns_unified_envelope(mocked_api):
    """When API returns 500, tool returns standard error envelope."""
    _mock_log(mocked_api, text="Internal server error", status_code=500)

    result = await _call()

    assert result["success"] is False
    assert result["error"]["tool"] == "get_publish_step_logs"
    assert result["error"]["type"] == "http_error"
    assert result["error"]["status_code"] == 500
