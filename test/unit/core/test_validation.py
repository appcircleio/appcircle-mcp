"""Unit tests for shared validation helpers (src/core/validation.py)."""

import pytest

from src.core.validation import path_segment, validate_date_format, validate_enum_list

TRAVERSAL_VALUES = [
    "../../../identity/v1/users",
    "..",
    ".",
    "abc/configurations",
    "abc\\def",
    "%2e%2e%2fidentity",
    "..%2f..%2fidentity",
    "abc?x=1",
    "abc#",
    "abc def",
    " abc",
    "",
    "a" * 129,
]

ALLOWED = {1: "iOS", 2: "Android"}


def test_validate_enum_list_none_returns_none():
    """None input (filter not provided) is valid -- returns None."""
    assert validate_enum_list(None, ALLOWED, "platform") is None


def test_validate_enum_list_all_valid_returns_none():
    """All values present in the allowed dict return None."""
    assert validate_enum_list([1, 2], ALLOWED, "platform") is None


def test_validate_enum_list_invalid_value_returns_message():
    """An out-of-enum value returns a descriptive error message."""
    message = validate_enum_list([1, 99], ALLOWED, "platform")

    assert message is not None
    assert "99" in message
    assert "platform" in message


def test_validate_date_format_none_returns_none():
    """None input (date filter not provided) is valid -- returns None."""
    assert validate_date_format(None, "start_date") is None


def test_validate_date_format_valid_date_returns_none():
    """A well-formed YYYY-MM-DD date returns None."""
    assert validate_date_format("2026-06-01", "start_date") is None


def test_validate_date_format_wrong_format_returns_message():
    """A date in the wrong format (e.g. slashes) returns an error message."""
    message = validate_date_format("2026/06/01", "start_date")

    assert message is not None
    assert "start_date" in message


def test_validate_date_format_invalid_calendar_date_returns_message():
    """A syntactically-shaped but calendar-invalid date (month 13) is rejected."""
    message = validate_date_format("2026-13-01", "start_date")

    assert message is not None


def test_validate_date_format_garbage_returns_message():
    """A non-date string returns an error message."""
    message = validate_date_format("not-a-date", "end_date")

    assert message is not None
    assert "end_date" in message


@pytest.mark.parametrize(
    "value",
    [
        "f4e4d8f9-ae28-4e82-a7bd-5e02338c2260",
        "15d2bb0bac20cd8a564d4dbdf7bf2948321f7908",
        "6512f0c1a2b3c4d5e6f70809",
        "step_1",
    ],
)
def test_path_segment_accepts_ids(value):
    """UUIDs, commit SHAs and other opaque IDs are returned unchanged."""
    assert path_segment(value, "profile_id") == value


@pytest.mark.parametrize("value", TRAVERSAL_VALUES)
def test_path_segment_rejects_unsafe_values(value):
    """Traversal, separators, encoded forms, query/fragment delimiters and whitespace raise ValueError."""
    with pytest.raises(ValueError, match="Invalid profile_id"):
        path_segment(value, "profile_id")


@pytest.mark.parametrize("value", [None, 123])
def test_path_segment_rejects_non_strings(value):
    """Non-string values raise ValueError."""
    with pytest.raises(ValueError):
        path_segment(value, "profile_id")
