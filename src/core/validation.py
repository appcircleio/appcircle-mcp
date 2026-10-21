"""Shared validation helpers for MCP tools."""

import re
from datetime import datetime
from typing import Dict, List, Optional

# IDs interpolated into API paths: UUIDs, commit SHAs, and other opaque IDs
_PATH_SEGMENT_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}")


def path_segment(value: str, field_name: str) -> str:
    """Return value if it is safe to use as a single URL path segment, else raise ValueError."""
    if not isinstance(value, str) or not _PATH_SEGMENT_PATTERN.fullmatch(value):
        raise ValueError(
            f"Invalid {field_name}: {value!r}. Expected an ID containing only letters, digits, '-' or '_'."
        )
    return value


def validate_enum_list(values: Optional[List[int]], allowed: Dict[int, str], field_name: str) -> Optional[str]:
    """Return an error message if any value is not in allowed, else None."""
    if values is None:
        return None
    invalid = [v for v in values if v not in allowed]
    if invalid:
        return f"Invalid {field_name}: {invalid}. Allowed values: {sorted(allowed)}"
    return None


def validate_date_format(value: Optional[str], field_name: str) -> Optional[str]:
    """Return an error message if value is not a valid YYYY-MM-DD date, else None."""
    if value is None:
        return None
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return f"Invalid {field_name}: {value!r}. Expected format: YYYY-MM-DD."
    return None
