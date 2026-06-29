"""Generic helpers and the MTTR / flaky-detection algorithms shared by the
build-insights report's sections.
"""

import re
from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

FAILURE_STATUSES = {1, 3}   # Failed, Timeout
SUCCESS_STATUS = 0          # status 2 (canceled) and 99 (unknown) are ignored by MTTR episode tracking

_FRACTIONAL_SECONDS = re.compile(r"\.(\d+)")


def parse_iso(timestamp: str) -> datetime:
    """Parse an Appcircle ISO 8601 timestamp (Z-suffixed) into a datetime.

    Appcircle emits a variable number of fractional-second digits (e.g.
    ".12"), but `datetime.fromisoformat` only accepts exactly 3 or 6 digits
    on Python <3.11. Normalize to microseconds so parsing is consistent
    across all supported Python versions.
    """
    timestamp = timestamp.replace("Z", "+00:00")
    match = _FRACTIONAL_SECONDS.search(timestamp)
    if match:
        microseconds = (match.group(1) + "000000")[:6]
        timestamp = f"{timestamp[:match.start()]}.{microseconds}{timestamp[match.end():]}"
    return datetime.fromisoformat(timestamp)


def percentile(sorted_values: List[float], pct: float) -> float:
    """Linear-interpolation percentile (numpy's default "linear" method).

    `sorted_values` must already be sorted ascending. No numpy dependency.
    """
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)


def field_present(builds: List[Dict[str, Any]], field: str) -> bool:
    """Whether at least one build has a non-null/non-empty value for `field`."""
    return any(b.get(field) not in (None, "", []) for b in builds)


def compute_mttr_episodes(builds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One entry per recovery episode -- a contiguous run of failures closed
    by the next success on the same profile+branch -- not one per failed build.

    Returns: [{"profile", "branch", "failure_start", "recovery_start",
               "duration_hours"}, ...]
    """
    by_combo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for build in builds:
        by_combo[(build["buildProfileName"], build["branchName"])].append(build)

    episodes: List[Dict[str, Any]] = []
    for (profile, branch), group in by_combo.items():
        ordered = sorted(group, key=lambda b: b["buildStartDate"])
        failure_start: Optional[str] = None
        for build in ordered:
            status = build["buildStatus"]
            if status in FAILURE_STATUSES:
                if failure_start is None:
                    failure_start = build["buildStartDate"]
            elif status == SUCCESS_STATUS and failure_start is not None:
                recovery_start = build["buildStartDate"]
                duration_hours = (
                    parse_iso(recovery_start) - parse_iso(failure_start)
                ).total_seconds() / 3600
                episodes.append({
                    "profile": profile,
                    "branch": branch,
                    "failure_start": failure_start,
                    "recovery_start": recovery_start,
                    "duration_hours": duration_hours,
                })
                failure_start = None
            # status 2 (canceled) or 99 (unknown): doesn't start, extend, or close an episode
        # an open failure_start here means the combo is still broken at period end; not recorded
    return episodes


def top_mttr_combos(episodes: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    """Top profile+branch combos by avg MTTR, longest first (most impactful)."""
    by_combo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        by_combo[(episode["profile"], episode["branch"])].append(episode)

    rows = [
        {
            "profile": profile,
            "branch": branch,
            "avg_hours": mean(e["duration_hours"] for e in group),
            "sequence_count": len(group),
        }
        for (profile, branch), group in by_combo.items()
    ]
    return sorted(rows, key=lambda r: r["avg_hours"], reverse=True)[:limit]


def compute_flaky_groups(builds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group by (profile, branch, workflow, commit_id). Flaky if the same
    commit produced both a success and a failure on that exact combo.

    Returns: [{"profile", "branch", "workflow", "commit_id", "build_count",
               "wasted_minutes"}, ...]
    """
    by_commit: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for build in builds:
        workflow = build.get("workflowName")
        commit_id = build.get("commitId")
        if workflow is None or commit_id is None:
            continue
        by_commit[(build["buildProfileName"], build["branchName"], workflow, commit_id)].append(build)

    flaky: List[Dict[str, Any]] = []
    for (profile, branch, workflow, commit_id), group in by_commit.items():
        statuses = {b["buildStatus"] for b in group}
        if SUCCESS_STATUS in statuses and statuses & FAILURE_STATUSES:
            flaky.append({
                "profile": profile,
                "branch": branch,
                "workflow": workflow,
                "commit_id": commit_id,
                "build_count": len(group),
                # includes every build in the group, including canceled runs
                "wasted_minutes": sum(b["buildDuration"] for b in group),
            })
    return flaky


def top_flaky_combos(flaky_groups: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    """Top profile+branch combos by wasted time, aggregating across workflows."""
    by_combo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for group in flaky_groups:
        by_combo[(group["profile"], group["branch"])].append(group)

    rows = [
        {
            "profile": profile,
            "branch": branch,
            "flaky_commit_count": len({g["commit_id"] for g in groups}),
            "wasted_minutes": sum(g["wasted_minutes"] for g in groups),
        }
        for (profile, branch), groups in by_combo.items()
    ]
    return sorted(rows, key=lambda r: r["wasted_minutes"], reverse=True)[:limit]
