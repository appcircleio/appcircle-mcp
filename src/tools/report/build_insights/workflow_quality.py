"""Compute functions for the build-insights report's Workflow Quality
section: tiered best-practice scoring against the Appcircle workflow
component catalog.

Framework variants (Flutter, React Native) are extra component *options*
within the same functional group, not separate groups -- a profile's
framework never needs to be classified up front. React Native has no
dedicated "build" component at all; it reuses the native iOS/Android build
steps, so it contributes no extra identifiers anywhere.
"""

from typing import Any, Dict, List, Optional

IOS_OS = 1
ANDROID_OS = 2

CRITICAL, IMPORTANT, ADVANCED = 1, 2, 3
TIER_POINTS = {CRITICAL: 60, IMPORTANT: 30, ADVANCED: 10}
TIER_NAMES = {CRITICAL: "Critical", IMPORTANT: "Important", ADVANCED: "Advanced"}

# Each group: name, tier, the set of componentTypes that satisfy it (any one
# enabled step matching is enough), and whether it's only expected on Push
# workflows (Versioning, Binary security).
IOS_GROUPS: List[Dict[str, Any]] = [
    {"name": "Git clone", "tier": CRITICAL, "identifiers": {"appcircle_git_clone"}, "push_only": False},
    {"name": "Dependencies", "tier": CRITICAL, "identifiers": {"appcircle_cocoapods", "appcircle_carthage", "appcircle_flutter_install"}, "push_only": False},
    {"name": "Build", "tier": CRITICAL, "identifiers": {"appcircle_ios_build_sign"}, "push_only": False},
    {"name": "Export build artifacts", "tier": CRITICAL, "identifiers": {"appcircle_export_build_artifacts"}, "push_only": False},
    {"name": "Cache pull", "tier": IMPORTANT, "identifiers": {"appcircle_cache_pull"}, "push_only": False},
    {"name": "Cache push", "tier": IMPORTANT, "identifiers": {"appcircle_cache_push"}, "push_only": False},
    {"name": "Versioning", "tier": IMPORTANT, "identifiers": {"appcircle_ios_build_version_increment"}, "push_only": True},
    {"name": "Test", "tier": IMPORTANT, "identifiers": {"appcircle_ios_test"}, "push_only": False},
    {"name": "Code quality", "tier": IMPORTANT, "identifiers": {"appcircle_swiftlint", "appcircle_sonarqube"}, "push_only": False},
    {"name": "Static security", "tier": ADVANCED, "identifiers": {"appcircle_snyk_scan_secure"}, "push_only": False},
    {"name": "File size check", "tier": ADVANCED, "identifiers": {"appcircle_filesize"}, "push_only": False},
    {"name": "Notify", "tier": ADVANCED, "identifiers": {"appcircle_azure_boards", "appcircle_jira"}, "push_only": False},
    {"name": "Binary security", "tier": ADVANCED, "identifiers": {"appcircle_ios_kobil_appshield_scanner", "appcircle_datatheorem", "appcircle_fod_mobile_assessment"}, "push_only": True},
]

ANDROID_GROUPS: List[Dict[str, Any]] = [
    {"name": "Git clone", "tier": CRITICAL, "identifiers": {"appcircle_git_clone"}, "push_only": False},
    {"name": "Build", "tier": CRITICAL, "identifiers": {"appcircle_android_build", "appcircle_android_flutter_build"}, "push_only": False},
    {"name": "Signing", "tier": CRITICAL, "identifiers": {"appcircle_android_sign", "appcircle_android_flutter_sign"}, "push_only": False},
    {"name": "Export build artifacts", "tier": CRITICAL, "identifiers": {"appcircle_export_build_artifacts"}, "push_only": False},
    {"name": "Cache pull", "tier": IMPORTANT, "identifiers": {"appcircle_cache_pull"}, "push_only": False},
    {"name": "Cache push", "tier": IMPORTANT, "identifiers": {"appcircle_cache_push"}, "push_only": False},
    {"name": "Versioning", "tier": IMPORTANT, "identifiers": {"appcircle_android_build_version_increment", "appcircle_android_flutter_build_version_increment"}, "push_only": True},
    {"name": "Code quality", "tier": IMPORTANT, "identifiers": {"appcircle_sonarqube"}, "push_only": False},
    {"name": "Static security", "tier": ADVANCED, "identifiers": {"appcircle_snyk_scan_secure"}, "push_only": False},
    {"name": "File size check", "tier": ADVANCED, "identifiers": {"appcircle_filesize"}, "push_only": False},
    {"name": "Notify", "tier": ADVANCED, "identifiers": {"appcircle_azure_boards", "appcircle_jira"}, "push_only": False},
    {"name": "Binary security", "tier": ADVANCED, "identifiers": {"appcircle_appsweep", "appcircle_datatheorem", "appcircle_fod_mobile_assessment"}, "push_only": True},
]

# Android has no "Test" group and no separate "Dependencies" group --
# dependency installation is part of the Build step (appcircle_android_build).


def groups_for_os(os_code: Optional[int]) -> List[Dict[str, Any]]:
    if os_code == IOS_OS:
        return IOS_GROUPS
    if os_code == ANDROID_OS:
        return ANDROID_GROUPS
    return []


def detect_os(curr_builds: List[Dict[str, Any]], profile: str) -> Optional[int]:
    """The `os` field (1=iOS, 2=Android) from any of the profile's build records."""
    for build in curr_builds:
        if build["buildProfileName"] == profile and build.get("os") is not None:
            return build["os"]
    return None


def group_present(steps: List[Dict[str, Any]], identifiers: set) -> bool:
    """True if any *enabled* step's component_type is in `identifiers`."""
    return any(step["enabled"] and step.get("component_type") in identifiers for step in steps)


def score_workflow(steps: List[Dict[str, Any]], os_code: Optional[int], is_push: bool) -> Optional[Dict[str, Any]]:
    """Tier 1/2/3 scores (each tier's points split evenly across its
    applicable groups) + the list of missing groups, for one workflow.
    `None` if `os_code` isn't recognized -- nothing to score against.
    """
    groups = groups_for_os(os_code)
    if not groups:
        return None

    tier_scores: Dict[int, float] = {}
    missing_groups: List[Dict[str, str]] = []

    for tier in (CRITICAL, IMPORTANT, ADVANCED):
        applicable = [g for g in groups if g["tier"] == tier and (is_push or not g["push_only"])]
        if not applicable:  # pragma: no cover -- no tier in the current catalog is all push_only
            tier_scores[tier] = TIER_POINTS[tier]
            continue

        present_count = 0
        for group in applicable:
            if group_present(steps, group["identifiers"]):
                present_count += 1
            else:
                missing_groups.append({"tier": TIER_NAMES[tier], "group": group["name"]})
        tier_scores[tier] = (present_count / len(applicable)) * TIER_POINTS[tier]

    return {
        "tier1_score": round(tier_scores[CRITICAL]),
        "tier2_score": round(tier_scores[IMPORTANT]),
        "tier3_score": round(tier_scores[ADVANCED]),
        "total_score": round(sum(tier_scores.values())),
        "missing_groups": missing_groups,
    }


def best_practice_checks(
    profile: str,
    os_code: Optional[int],
    push_workflow_name: Optional[str],
    push_steps: Optional[List[Dict[str, Any]]],
    pr_workflow_name: Optional[str],
    pr_steps: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Versioning not automated (Push, critical) and custom script not from
    Git (Push+PR, advisory). Does not check "no PR workflow configured":
    with no `triggers` field here, this function can't distinguish "no PR
    workflow exists" from "no PR was opened this period".
    """
    issues: List[Dict[str, Any]] = []

    if push_steps is not None:
        versioning_group = next(
            (g for g in groups_for_os(os_code) if g["name"] == "Versioning"), None
        )
        if versioning_group and not group_present(push_steps, versioning_group["identifiers"]):
            issues.append({
                "check": "versioning_not_automated",
                "severity": "critical",
                "profile": profile,
                "workflow": push_workflow_name,
            })

    for workflow_name, steps in ((push_workflow_name, push_steps), (pr_workflow_name, pr_steps)):
        if not steps:
            continue
        inline_count = sum(
            1 for s in steps if s["enabled"] and s.get("component_type") == "appcircle_custom_script"
        )
        if inline_count:
            issues.append({
                "check": "custom_script_not_from_git",
                "severity": "advisory",
                "profile": profile,
                "workflow": workflow_name,
                "count": inline_count,
            })

    return issues
