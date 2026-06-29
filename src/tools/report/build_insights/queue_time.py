"""Compute functions for the build-insights report's Queue Time section.

This section is org-wide and current-period-only -- no per-profile
breakdown, no previous-period comparison. Operates on records from
GET /report/v1/build/queue-waiting, where `buildDuration` means queue wait
time in minutes -- not execution time, which is what the same field name
means on /report/v2/build.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .shared import parse_iso, percentile

IN_PROGRESS_STATUSES = {90, 91, 92}


def _valid_waits(queue_builds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Excludes builds with an in-progress status."""
    return [b for b in queue_builds if b.get("buildStatus") not in IN_PROGRESS_STATUSES]


def compute_queue_wait_summary(queue_builds: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Tiles: total/avg/p50/p95 wait in minutes, plus the build count they're
    based on. `None` if there's nothing valid to summarize.

    Canceled and failed builds are included.
    """
    valid = _valid_waits(queue_builds)
    if not valid:
        return None

    waits = sorted(b["buildDuration"] for b in valid)
    total = sum(waits)
    return {
        "total_wait_minutes": total,
        "avg_wait_minutes": total / len(waits),
        "p50_wait_minutes": percentile(waits, 50),
        "p95_wait_minutes": percentile(waits, 95),
        "build_count": len(waits),
    }


def plan_wait_breakdown(summary: Optional[Dict[str, Any]]) -> Optional[Dict[str, float]]:
    """Org-wide queue wait time in minutes by machine plan, from the
    queue-waiting endpoint's `summary.standard/velocity/ultra` fields.
    No per-build plan attribution is available.

    `None` if `summary` is missing or carries none of the three fields.
    """
    if not summary or not any(key in summary for key in ("standard", "velocity", "ultra")):
        return None

    return {
        "standard_wait_minutes": summary.get("standard", 0.0),
        "velocity_wait_minutes": summary.get("velocity", 0.0),
        "ultra_wait_minutes": summary.get("ultra", 0.0),
    }


def daily_queue_wait_trend(queue_builds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Mean queue wait per calendar day of `buildStartDate`. Days with no
    valid builds are omitted, not zero-filled.
    """
    by_day: Dict[Any, List[float]] = defaultdict(list)
    for build in _valid_waits(queue_builds):
        day = parse_iso(build["buildStartDate"]).date()
        by_day[day].append(build["buildDuration"])

    return [
        {"date": day.isoformat(), "avg_wait_minutes": sum(waits) / len(waits)}
        for day, waits in sorted(by_day.items())
    ]
