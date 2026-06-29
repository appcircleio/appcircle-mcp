"""Compute functions for the build-insights report's Artifact Health section.
Every function operates on already-fetched build records -- no I/O happens here.
"""

from collections import defaultdict
from statistics import mean
from typing import Any, Dict, List, Optional

from .shared import SUCCESS_STATUS

# Installable artifact extensions considered for primary-artifact sizing.
ARTIFACT_SUFFIXES = (".ipa", ".apk", ".aab")


def _primary_artifact_size(build: Dict[str, Any]) -> Optional[float]:
    """The build's primary artifact size in MB: `targetFile` if present,
    otherwise the largest installable artifact (.ipa/.apk/.aab) in `artifactItems`."""
    target_file = build.get("targetFile")
    if target_file:
        return target_file.get("fileSize")

    candidates = [
        item for item in (build.get("artifactItems") or [])
        if str(item.get("filename", "")).lower().endswith(ARTIFACT_SUFFIXES)
    ]
    if not candidates:
        return None
    return max(item.get("fileSize", 0) for item in candidates)


def _artifact_sizes_by_profile(builds: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """Group successful builds' primary artifact sizes by profile in one
    pass, instead of rescanning the full build list once per top profile."""
    sizes_by_profile: Dict[str, List[float]] = defaultdict(list)
    for build in builds:
        if build["buildStatus"] != SUCCESS_STATUS:
            continue
        size = _primary_artifact_size(build)
        if size is not None:
            sizes_by_profile[build["buildProfileName"]].append(size)
    return sizes_by_profile


def artifact_size_per_profile(
    curr_builds: List[Dict[str, Any]],
    prev_builds: List[Dict[str, Any]],
    top_profiles: List[str],
) -> List[Dict[str, Any]]:
    """Average primary artifact size per top profile, current vs. previous
    period. A profile with no artifact in the current period is skipped
    entirely (not zero-filled) -- there's nothing to compare. A profile with
    artifacts now but none in the previous period gets `delta_mb`/`delta_pct`
    of `None` -- no baseline, not a 0% change.
    """
    curr_sizes_by_profile = _artifact_sizes_by_profile(curr_builds)
    prev_sizes_by_profile = _artifact_sizes_by_profile(prev_builds)

    rows = []
    for profile in top_profiles:
        curr_sizes = curr_sizes_by_profile.get(profile, [])
        if not curr_sizes:
            continue
        current_avg_size = mean(curr_sizes)

        prev_sizes = prev_sizes_by_profile.get(profile, [])
        prev_avg_size = mean(prev_sizes) if prev_sizes else None

        if prev_avg_size:
            delta_mb = current_avg_size - prev_avg_size
            delta_pct = delta_mb / prev_avg_size * 100
        else:
            delta_mb = None
            delta_pct = None

        rows.append({
            "profile": profile,
            "current_avg_size_mb": current_avg_size,
            "prev_avg_size_mb": prev_avg_size,
            "delta_mb": delta_mb,
            "delta_pct": delta_pct,
        })
    return sorted(rows, key=lambda r: r["current_avg_size_mb"], reverse=True)


def biggest_grower_and_shrinker(per_profile_rows: List[Dict[str, Any]]) -> Dict[str, Optional[Dict[str, Any]]]:
    """The profile with the largest artifact-size increase and the one with
    the largest decrease. A profile with no previous-period baseline
    (`delta_mb` is `None`) never qualifies as either."""
    changed = [r for r in per_profile_rows if r["delta_mb"] is not None]
    growers = [r for r in changed if r["delta_mb"] > 0]
    shrinkers = [r for r in changed if r["delta_mb"] < 0]
    return {
        "grower": max(growers, key=lambda r: r["delta_mb"]) if growers else None,
        "shrinker": min(shrinkers, key=lambda r: r["delta_mb"]) if shrinkers else None,
    }
