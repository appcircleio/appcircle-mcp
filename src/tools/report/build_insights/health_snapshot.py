"""Compute functions for the build-insights report's Health Snapshot + Trends
section. Every function operates on already-fetched build records (and, for
`inactive_profiles`, the full profiles list) -- no I/O happens here.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from .shared import SUCCESS_STATUS, field_present, parse_iso, percentile

INACTIVITY_WINDOW_DAYS = 30
EXCLUDED_INITIATED_BY = {None, "", "N/A", "00000000-0000-0000-0000-000000000000"}


def _period_counts(builds: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(builds)
    success = sum(1 for b in builds if b["buildStatus"] == SUCCESS_STATUS)
    failed = sum(1 for b in builds if b["buildStatus"] in (1, 3))
    canceled = sum(1 for b in builds if b["buildStatus"] == 2)
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "canceled": canceled,
        "success_rate": (success / total * 100) if total else 0.0,
        "failure_rate": (failed / total * 100) if total else 0.0,
        "canceled_rate": (canceled / total * 100) if total else 0.0,
    }


def compute_summary(curr_builds: List[Dict[str, Any]], prev_builds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Totals/rates for both periods plus deltas.

    `total`'s delta is a relative percent change. `success_rate`/
    `failure_rate`/`canceled_rate` deltas are percentage-point differences
    (pp), not a percent change of a percentage.
    """
    current = _period_counts(curr_builds)
    previous = _period_counts(prev_builds)
    has_baseline = previous["total"] > 0

    def pct_delta(curr: int, prev: int) -> Optional[float]:
        return ((curr - prev) / prev * 100) if prev else None

    def pp_delta(curr_rate: float, prev_rate: float) -> Optional[float]:
        return (curr_rate - prev_rate) if has_baseline else None

    delta = {
        "total_pct": pct_delta(current["total"], previous["total"]),
        "success_rate_pp": pp_delta(current["success_rate"], previous["success_rate"]),
        "failure_rate_pp": pp_delta(current["failure_rate"], previous["failure_rate"]),
        "canceled_rate_pp": pp_delta(current["canceled_rate"], previous["canceled_rate"]),
    }
    return {"current": current, "previous": previous, "delta": delta}


def top_active_profiles(curr_builds: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    by_profile: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for build in curr_builds:
        by_profile[build["buildProfileName"]].append(build)

    rows = []
    for profile, group in by_profile.items():
        total = len(group)
        success = sum(1 for b in group if b["buildStatus"] == SUCCESS_STATUS)
        rows.append({
            "profile": profile,
            "build_count": total,
            "success_rate": (success / total * 100) if total else 0.0,
        })
    return sorted(rows, key=lambda r: r["build_count"], reverse=True)[:limit]


def inactive_profiles(all_profiles: List[Dict[str, Any]], as_of: date) -> List[Dict[str, Any]]:
    """Profiles with no builds in the trailing 30 days from `as_of` (the
    report's `current_end`, not wall-clock "today").

    Uses `lastBuildDate` directly from `/build/v2/profiles`; no
    build-history cross-referencing needed.
    """
    inactive = []
    for profile in all_profiles:
        last_build_date = profile.get("lastBuildDate")
        is_inactive = (
            last_build_date is None
            or (as_of - parse_iso(last_build_date).date()).days > INACTIVITY_WINDOW_DAYS
        )
        if is_inactive:
            inactive.append({
                "profile": profile.get("name"),
                "last_build_date": last_build_date,
            })
    return inactive


def top_build_activity(curr_builds: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    by_combo: Dict[Any, int] = defaultdict(int)
    for build in curr_builds:
        by_combo[(build["buildProfileName"], build["branchName"])] += 1

    rows = [
        {"profile": profile, "branch": branch, "build_count": count}
        for (profile, branch), count in by_combo.items()
    ]
    return sorted(rows, key=lambda r: r["build_count"], reverse=True)[:limit]


def _top_initiators(builds: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = defaultdict(int)
    for build in builds:
        initiator = build.get("initiatedBy")
        if initiator in EXCLUDED_INITIATED_BY:
            continue
        counts[initiator] += 1
    rows = [{"initiated_by": initiator, "build_count": count} for initiator, count in counts.items()]
    return sorted(rows, key=lambda r: r["build_count"], reverse=True)[:limit]


def top_triggers(curr_builds: List[Dict[str, Any]], limit: int = 5) -> Optional[Dict[str, Any]]:
    """Manual (triggerCategory == 0) vs. automated (otherwise), grouped by initiatedBy."""
    if not field_present(curr_builds, "triggerCategory") or not field_present(curr_builds, "initiatedBy"):
        return None
    manual = [b for b in curr_builds if b.get("triggerCategory") == 0]
    automated = [b for b in curr_builds if b.get("triggerCategory") != 0]
    return {
        "manual": _top_initiators(manual, limit),
        "automated": _top_initiators(automated, limit),
    }


def daily_series(curr_builds: List[Dict[str, Any]], current_start: date, current_end: date) -> List[Dict[str, Any]]:
    """Bucket builds by calendar date; every day in range appears, zero-filled if empty."""
    empty_bucket = {"total": 0, "success": 0, "failed": 0, "canceled": 0, "timeout": 0}
    buckets: Dict[date, Dict[str, int]] = defaultdict(lambda: dict(empty_bucket))

    for build in curr_builds:
        day = parse_iso(build["buildStartDate"]).date()
        bucket = buckets[day]
        bucket["total"] += 1
        status = build["buildStatus"]
        if status == SUCCESS_STATUS:
            bucket["success"] += 1
        elif status == 2:
            bucket["canceled"] += 1
        elif status == 3:
            bucket["failed"] += 1
            bucket["timeout"] += 1
        elif status == 1:
            bucket["failed"] += 1

    series = []
    day = current_start
    while day <= current_end:
        bucket = buckets.get(day, empty_bucket)
        total = bucket["total"]
        series.append({
            "date": day.isoformat(),
            "total": total,
            "success": bucket["success"],
            "failed": bucket["failed"],
            "canceled": bucket["canceled"],
            "timeout": bucket["timeout"],
            "pass_rate": (bucket["success"] / total * 100) if total else 0.0,
            "fail_rate": (bucket["failed"] / total * 100) if total else 0.0,
        })
        day += timedelta(days=1)
    return series


def per_profile_duration(
    curr_builds: List[Dict[str, Any]],
    prev_builds: List[Dict[str, Any]],
    top_profiles: List[str],
) -> List[Dict[str, Any]]:
    """P50/P95/ratio/consistency per top profile, plus trend vs. previous period P50.
    `buildDuration` is in minutes -- no unit conversion needed."""
    rows = []
    for profile in top_profiles:
        curr_durations = sorted(
            b["buildDuration"] for b in curr_builds
            if b["buildProfileName"] == profile and b["buildStatus"] == SUCCESS_STATUS
        )
        if not curr_durations:
            continue

        p50 = percentile(curr_durations, 50)
        p95 = percentile(curr_durations, 95)
        ratio = (p95 / p50) if p50 else 0.0
        if ratio < 1.5:
            consistency = "consistent"
        elif ratio <= 2.0:
            consistency = "moderate"
        else:
            consistency = "high variance"

        prev_durations = sorted(
            b["buildDuration"] for b in prev_builds
            if b["buildProfileName"] == profile and b["buildStatus"] == SUCCESS_STATUS
        )
        trend = "stable"
        if prev_durations:
            prev_p50 = percentile(prev_durations, 50)
            if prev_p50:
                change_pct = (p50 - prev_p50) / prev_p50 * 100
                if change_pct > 10:
                    trend = "slower"
                elif change_pct < -10:
                    trend = "faster"

        rows.append({
            "profile": profile,
            "p50": p50,
            "p95": p95,
            "ratio": ratio,
            "consistency": consistency,
            "trend": trend,
        })
    return rows


def per_profile_duration_series(
    curr_builds: List[Dict[str, Any]],
    current_start: date,
    current_end: date,
    top_profiles: List[str],
) -> List[Dict[str, Any]]:
    """Daily P50 build duration per top profile -- the underlying series for
    a per-profile duration line chart, separate from `per_profile_duration`'s
    period-level aggregate row.

    A day with fewer than 2 successful builds for a profile gets `p50: None`
    rather than 0 or an omitted point.
    """
    by_profile_day: Dict[str, Dict[date, List[float]]] = defaultdict(lambda: defaultdict(list))
    for build in curr_builds:
        profile = build["buildProfileName"]
        if build["buildStatus"] != SUCCESS_STATUS or profile not in top_profiles:
            continue
        day = parse_iso(build["buildStartDate"]).date()
        by_profile_day[profile][day].append(build["buildDuration"])

    rows = []
    for profile in top_profiles:
        day_durations = by_profile_day.get(profile, {})
        series = []
        day = current_start
        while day <= current_end:
            durations = day_durations.get(day, [])
            p50 = percentile(sorted(durations), 50) if len(durations) >= 2 else None
            series.append({"date": day.isoformat(), "p50": p50})
            day += timedelta(days=1)
        rows.append({"profile": profile, "series": series})
    return rows
