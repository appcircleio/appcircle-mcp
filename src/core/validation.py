"""Shared validation helpers for MCP tools."""

from datetime import datetime
from typing import Dict, List, Optional


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
