"""Unit tests for shared validation helpers (src/core/validation.py)."""

from src.core.validation import validate_date_format, validate_enum_list

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
