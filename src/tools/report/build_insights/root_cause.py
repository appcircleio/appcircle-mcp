"""Compute functions for the build-insights report's Root Cause section.
Every function operates on already-fetched current-period build records --
no I/O happens here.
"""

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .shared import (
    FAILURE_STATUSES,
    SUCCESS_STATUS,
    compute_flaky_groups,
    compute_mttr_episodes,
    field_present,
    top_flaky_combos,
    top_mttr_combos,
)


def _split_failed_step(failed_step: Optional[str]) -> List[str]:
    if not failed_step:
        return []
    return [s.strip() for s in failed_step.split(",") if s.strip()]


def top_failing_steps(
    curr_builds: List[Dict[str, Any]],
    limit: int = 5,
    combo_limit: int = 5,
) -> Optional[List[Dict[str, Any]]]:
    """Top failing steps by count, with their top profile+branch combos.

    Scoped to builds that actually failed (status 1/3) only. `failedStep`
    is also populated on warned-but-successful builds, surfaced separately
    via `warning_hotspot_cards`.

    The `field_present` gate checks failed builds only, since `failedStep`
    is null on successful builds and checking against the full set would
    misread a clean period as a missing field.
    """
    failed_builds_all = [b for b in curr_builds if b["buildStatus"] in FAILURE_STATUSES]
    if failed_builds_all and not field_present(failed_builds_all, "failedStep"):
        return None

    failed_builds = [b for b in failed_builds_all if b.get("failedStep")]
    if not failed_builds:
        return []

    step_counts: Counter = Counter()
    step_combo_counts: Dict[str, Counter] = defaultdict(Counter)

    for build in failed_builds:
        combo: Tuple[str, str] = (build["buildProfileName"], build["branchName"])
        for step in _split_failed_step(build["failedStep"]):
            step_counts[step] += 1
            step_combo_counts[step][combo] += 1

    total_failed = len(failed_builds)
    rows = []
    for step, count in step_counts.most_common(limit):
        top_combos = [
            {"profile": profile, "branch": branch, "count": combo_count}
            for (profile, branch), combo_count in step_combo_counts[step].most_common(combo_limit)
        ]
        rows.append({
            "step": step,
            "count": count,
            "pct_of_failed": (count / total_failed * 100) if total_failed else 0.0,
            "top_combos": top_combos,
        })
    return rows


def mttr_cards(curr_builds: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    """Top profile+branch combos by mean time to recovery."""
    episodes = compute_mttr_episodes(curr_builds)
    return top_mttr_combos(episodes, limit)


def flaky_cards(curr_builds: List[Dict[str, Any]], limit: int = 3) -> Optional[List[Dict[str, Any]]]:
    """Top profile+branch combos by wasted build time from flaky commits."""
    if not field_present(curr_builds, "workflowName") or not field_present(curr_builds, "commitId"):
        return None
    flaky_groups = compute_flaky_groups(curr_builds)
    return top_flaky_combos(flaky_groups, limit)


def warning_hotspot_cards(curr_builds: List[Dict[str, Any]], limit: int = 3) -> Optional[List[Dict[str, Any]]]:
    """Top profile+branch combos by warned-build count, with their most common warning step."""
    if not field_present(curr_builds, "hasWarning"):
        return None

    warned_builds = [b for b in curr_builds if b.get("hasWarning")]
    by_combo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for build in warned_builds:
        by_combo[(build["buildProfileName"], build["branchName"])].append(build)

    rows = []
    for (profile, branch), group in by_combo.items():
        step_counter: Counter = Counter()
        for build in group:
            step_counter.update(_split_failed_step(build.get("failedStep")))
        top_step = step_counter.most_common(1)[0][0] if step_counter else None
        rows.append({
            "profile": profile,
            "branch": branch,
            "warned_count": len(group),
            "top_warning_step": top_step,
        })
    return sorted(rows, key=lambda r: r["warned_count"], reverse=True)[:limit]


def zero_success_workflow_cards(curr_builds: List[Dict[str, Any]], limit: int = 3) -> Optional[List[Dict[str, Any]]]:
    """(profile, workflow) combos with >=3 runs and zero successful builds."""
    if not field_present(curr_builds, "workflowName"):
        return None

    by_combo: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for build in curr_builds:
        workflow = build.get("workflowName")
        if workflow is None:
            continue
        by_combo[(build["buildProfileName"], workflow)].append(build)

    rows = []
    for (profile, workflow), group in by_combo.items():
        if len(group) < 3 or any(b["buildStatus"] == SUCCESS_STATUS for b in group):
            continue
        step_counter: Counter = Counter()
        for build in group:
            step_counter.update(_split_failed_step(build.get("failedStep")))
        always_failing_step = step_counter.most_common(1)[0][0] if step_counter else None
        rows.append({
            "profile": profile,
            "workflow": workflow,
            "run_count": len(group),
            "always_failing_step": always_failing_step,
        })
    return sorted(rows, key=lambda r: r["run_count"], reverse=True)[:limit]
