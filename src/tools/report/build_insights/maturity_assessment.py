"""Compute functions for the build-insights report's Maturity Assessment
section: Reliability (30%) + Discipline (30%) + Speed (15%) + Security (25%)
combined into one overall score, plus a rule-based Top Improvements list.

This module does no I/O and largely recombines pieces already computed for
other sections: Reliability's success-rate/MTTR/flaky factors reuse
`shared.py`; Speed reuses `health_snapshot.per_profile_duration`'s P95/P50
ratio; Discipline's workflow-completeness half reuses Workflow Quality's
per-profile scores; Security resolves signing-identity expiry/env-var usage
from `profile_configuration.py`'s fetches. The warning-hotspot factor and
the PR-workflow-configured check are self-contained.
"""

from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

from .shared import SUCCESS_STATUS, compute_flaky_groups, compute_mttr_episodes, field_present, parse_iso
from .workflow_quality import detect_os

OVERALL_WEIGHTS = {"reliability": 0.30, "discipline": 0.30, "speed": 0.15, "security": 0.25}


def _breakpoint_score(value: float, breakpoints: List[Any]) -> int:
    """`breakpoints` is [(threshold, score), ...] sorted by descending
    threshold, with a final (None, score) catch-all for "else"."""
    for threshold, score in breakpoints:
        if threshold is None or value >= threshold:
            return score
    return breakpoints[-1][1]  # pragma: no cover -- last entry's threshold is always None


def success_rate_factor(curr_builds: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(curr_builds)
    success = sum(1 for b in curr_builds if b["buildStatus"] == SUCCESS_STATUS)
    success_rate = (success / total) if total else 0.0
    factor_score = _breakpoint_score(success_rate, [
        (0.95, 100), (0.90, 90), (0.85, 80), (0.80, 70),
        (0.75, 60), (0.70, 50), (0.60, 40), (None, 20),
    ])
    return {"value": success_rate, "factor_score": factor_score}


def mttr_factor(curr_builds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Org-wide, not top-5-scoped. No recovery episodes this period is
    treated as a perfect score (genuine zero-incidents outcome, not missing data)."""
    episodes = compute_mttr_episodes(curr_builds)
    avg_hours = mean(e["duration_hours"] for e in episodes) if episodes else 0.0
    factor_score = _breakpoint_score(-avg_hours, [
        (-1, 100), (-2, 90), (-3, 80), (-4, 70),
        (-6, 60), (-8, 50), (-12, 40), (None, 20),
    ])
    return {"value_hours": avg_hours, "factor_score": factor_score}


def _rate_factor_score(rate: float) -> int:
    """Shared breakpoint table for the flaky and warning-hotspot factors --
    both map a 0-1 affected-rate to the same 100/80/60/40/20 scale."""
    return _breakpoint_score(-rate, [(0, 100), (-0.2, 80), (-0.4, 60), (-0.6, 40), (None, 20)])


def flaky_factor(curr_builds: List[Dict[str, Any]], top_profiles: List[str]) -> Dict[str, Any]:
    flaky_groups = compute_flaky_groups(curr_builds)
    flaky_profiles = {g["profile"] for g in flaky_groups}
    count = sum(1 for p in top_profiles if p in flaky_profiles)
    rate = (count / len(top_profiles)) if top_profiles else 0.0
    return {"count": count, "factor_score": _rate_factor_score(rate)}


def warning_hotspot_factor(curr_builds: List[Dict[str, Any]], top_profiles: List[str]) -> Optional[Dict[str, Any]]:
    """A profile is a hotspot if >=30% of its *successful* builds this period
    have `hasWarning == true`. `None` if `hasWarning` is absent from every record."""
    if not field_present(curr_builds, "hasWarning"):
        return None

    count = 0
    for profile in top_profiles:
        successful = [b for b in curr_builds if b["buildProfileName"] == profile and b["buildStatus"] == SUCCESS_STATUS]
        if not successful:
            continue
        warned = sum(1 for b in successful if b.get("hasWarning"))
        if warned / len(successful) >= 0.30:
            count += 1

    rate = (count / len(top_profiles)) if top_profiles else 0.0
    return {"count": count, "factor_score": _rate_factor_score(rate)}


def reliability_score(curr_builds: List[Dict[str, Any]], top_profiles: List[str]) -> Dict[str, Any]:
    """Combines the four factors. If the warning-hotspot factor is
    unavailable, its 20% weight is redistributed proportionally across the
    other three."""
    factors = {
        "success_rate": success_rate_factor(curr_builds),
        "mttr": mttr_factor(curr_builds),
        "flaky": flaky_factor(curr_builds, top_profiles),
        "warning_hotspots": warning_hotspot_factor(curr_builds, top_profiles),
    }
    weights = {"success_rate": 0.30, "mttr": 0.30, "flaky": 0.20, "warning_hotspots": 0.20}
    if factors["warning_hotspots"] is None:
        del weights["warning_hotspots"]
        weight_total = sum(weights.values())
        weights = {k: v / weight_total for k, v in weights.items()}

    score = round(sum(factors[k]["factor_score"] * w for k, w in weights.items()))
    return {"score": score, "factors": factors}


def discipline_score(
    per_profile_quality: List[Dict[str, Any]],
    workflow_quality_issues: List[Dict[str, Any]],
    pr_configured_by_profile: Dict[str, Optional[bool]],
    top_profiles: List[str],
) -> Optional[Dict[str, Any]]:
    """`None` if no workflow YAML was resolved for any top-5 profile this period."""
    workflow_scores = [
        row[side]["total_score"]
        for row in per_profile_quality
        for side in ("push", "pr")
        if row.get(side)
    ]
    if not workflow_scores:
        return None
    wf_completeness_score = mean(workflow_scores)

    versioning_applicable = sum(1 for row in per_profile_quality if row.get("push"))
    versioning_failing = {
        issue["profile"] for issue in workflow_quality_issues if issue["check"] == "versioning_not_automated"
    }
    versioning_passing = versioning_applicable - len(versioning_failing)

    git_scripts_failing = {
        issue["profile"] for issue in workflow_quality_issues if issue["check"] == "custom_script_not_from_git"
    }
    git_scripts_passing = len(top_profiles) - len(git_scripts_failing)

    # `None` (unresolved profile) is excluded from the applicable population, not scored as unconfigured.
    pr_check_applicable = [p for p in top_profiles if pr_configured_by_profile.get(p) is not None]
    pr_configured_passing = sum(1 for p in pr_check_applicable if pr_configured_by_profile.get(p))

    check_scores = [
        (versioning_passing / versioning_applicable) * (100 / 3) if versioning_applicable else 0.0,
        (git_scripts_passing / len(top_profiles)) * (100 / 3) if top_profiles else 0.0,
        (pr_configured_passing / len(pr_check_applicable)) * (100 / 3) if pr_check_applicable else 0.0,
    ]
    bp_score = min(100.0, sum(check_scores))

    score = round(wf_completeness_score * 0.50 + bp_score * 0.50)
    return {"score": score, "wf_completeness_score": round(wf_completeness_score), "bp_score": round(bp_score)}


def _consistency_band(ratio: float) -> str:
    """Same consistent/moderate/high-variance bands as
    `health_snapshot.per_profile_duration`'s per-profile labeling."""
    if ratio < 1.5:
        return "consistent"
    if ratio <= 2.0:
        return "moderate"
    return "high variance"


def speed_score(duration_rows: List[Dict[str, Any]], top_profile_rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Build-count-weighted consistency: the share of top-profile build
    volume coming from profiles with a P95/P50 ratio under 1.5, plus a
    build-count-weighted average ratio and consistency band. `None` if no
    top profile has a successful build this period to compute a ratio from.
    """
    if not duration_rows:
        return None

    build_count_by_profile = {row["profile"]: row["build_count"] for row in top_profile_rows}
    total = sum(build_count_by_profile.get(row["profile"], 0) for row in duration_rows)
    if not total:
        return None

    consistent = sum(
        build_count_by_profile.get(row["profile"], 0) for row in duration_rows if row["ratio"] < 1.5
    )
    weighted_avg_ratio = sum(
        row["ratio"] * build_count_by_profile.get(row["profile"], 0) for row in duration_rows
    ) / total

    return {
        "score": round(consistent / total * 100),
        "weighted_avg_ratio": weighted_avg_ratio,
        "consistency": _consistency_band(weighted_avg_ratio),
    }


def _resolve_signing_identity(
    entity_id: str,
    certificates_by_id: Dict[str, Dict[str, Any]],
    provisioning_profiles_by_id: Dict[str, Dict[str, Any]],
    keystores_by_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Resolve `entity_id` by membership across the three signing-identity id
    sets, rather than decoding `signingIdentityType`. Each endpoint's `id` is
    a UUID, effectively globally unique across the three lists, so whichever
    list matches determines both the type and the `expireDate`."""
    if entity_id in certificates_by_id:
        record, identity_type = certificates_by_id[entity_id], "certificate"
    elif entity_id in provisioning_profiles_by_id:
        record, identity_type = provisioning_profiles_by_id[entity_id], "provisioning_profile"
    elif entity_id in keystores_by_id:
        record, identity_type = keystores_by_id[entity_id], "keystore"
    else:
        return None

    expire_date = record.get("expireDate")
    if not expire_date:
        return None
    try:
        parsed_expiry = parse_iso(expire_date)
    except ValueError:
        return None

    return {
        "type": identity_type,
        "id": entity_id,
        "name": record.get("name"),
        "expire_date": expire_date,
        "_parsed_expiry": parsed_expiry,
    }


def security_score(
    configs_by_profile: Dict[str, Optional[Dict[str, Any]]],
    top_profiles: List[str],
    certificates: Optional[List[Dict[str, Any]]],
    provisioning_profiles: Optional[List[Dict[str, Any]]],
    keystores: Optional[List[Dict[str, Any]]],
    now: datetime,
) -> Optional[Dict[str, Any]]:
    """`None` if no top-5 profile resolved a configuration this period, or if
    any of the three signing-identity lists is `None` (fetch failed).

    Distinct signing identities referenced by the top-5 profiles' resolved
    configurations are deduped by id and flagged if within 30 days of
    `expireDate` (including already expired, i.e. negative
    `days_until_expiry`). Zero referenced identities scores 100 (genuine
    zero risk, e.g. an unsigned configuration).
    """
    if certificates is None or provisioning_profiles is None or keystores is None:
        return None

    resolved_profiles = [p for p in top_profiles if configs_by_profile.get(p) is not None]
    if not resolved_profiles:
        return None

    certificates_by_id = {c["id"]: c for c in certificates if c.get("id")}
    provisioning_profiles_by_id = {p["id"]: p for p in provisioning_profiles if p.get("id")}
    keystores_by_id = {k["id"]: k for k in keystores if k.get("id")}

    identities: Dict[str, Dict[str, Any]] = {}
    for profile in resolved_profiles:
        for raw_identity in configs_by_profile[profile]["signing_identities"]:
            entity_id = raw_identity.get("entityId")
            if not entity_id:
                continue
            resolved = _resolve_signing_identity(
                entity_id, certificates_by_id, provisioning_profiles_by_id, keystores_by_id
            )
            if resolved is None:
                continue
            if entity_id not in identities:
                identities[entity_id] = {**resolved, "profiles": set()}
            identities[entity_id]["profiles"].add(profile)

    expiring_soon = sorted(
        (
            {
                "type": identity["type"],
                "id": identity["id"],
                "name": identity["name"],
                "expire_date": identity["expire_date"],
                "days_until_expiry": (identity["_parsed_expiry"] - now).days,
                "profiles": sorted(identity["profiles"]),
            }
            for identity in identities.values()
            if (identity["_parsed_expiry"] - now).days <= 30
        ),
        key=lambda item: item["days_until_expiry"],
    )
    signing_health_score = (
        round((len(identities) - len(expiring_soon)) / len(identities) * 100) if identities else 100
    )

    without_env_vars = sorted(p for p in resolved_profiles if not configs_by_profile[p]["environment_variables"])
    env_var_usage_score = round((len(resolved_profiles) - len(without_env_vars)) / len(resolved_profiles) * 100)

    return {
        "score": round(signing_health_score * 0.70 + env_var_usage_score * 0.30),
        "signing_health_score": signing_health_score,
        "env_var_usage_score": env_var_usage_score,
        "expiring_soon": expiring_soon,
        "profiles_without_env_vars": without_env_vars,
    }


def combine_overall_score(
    reliability: Optional[int],
    discipline: Optional[int],
    speed: Optional[int],
    security: Optional[int],
) -> Dict[str, Any]:
    """Weighted combination of reliability/discipline/speed/security,
    renormalized across whichever sub-scores are actually available
    (missing scores are excluded, not treated as zero)."""
    available = {
        k: v for k, v in
        {"reliability": reliability, "discipline": discipline, "speed": speed, "security": security}.items()
        if v is not None
    }
    weight_total = sum(OVERALL_WEIGHTS[k] for k in available)
    overall = round(sum(v * OVERALL_WEIGHTS[k] / weight_total for k, v in available.items())) if weight_total else 0

    label = _breakpoint_score(overall, [
        (80, "Optimizing"), (65, "Advancing"), (45, "Practicing"), (None, "Developing"),
    ])
    return {"overall_score": overall, "label": label}


def top_improvements(
    curr_builds: List[Dict[str, Any]],
    top_profiles: List[str],
    duration_rows: List[Dict[str, Any]],
    workflow_quality_issues: List[Dict[str, Any]],
    pr_configured_by_profile: Dict[str, Optional[bool]],
    security: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Rule-based, data only (no prose) -- the calling LLM writes any
    narrative. Fixed priority order: critical (flaky, outlier duration,
    expiring signing identities) before advisory (custom scripts, PR
    config, versioning, env vars)."""
    improvements: List[Dict[str, Any]] = []

    flaky_groups = compute_flaky_groups(curr_builds)
    flaky_profiles = sorted({g["profile"] for g in flaky_groups} & set(top_profiles))
    if flaky_profiles:
        improvements.append({"check": "resolve_flaky_profiles", "severity": "critical", "profiles": flaky_profiles})

    if security and security["expiring_soon"]:
        expiring_profiles = sorted({p for item in security["expiring_soon"] for p in item["profiles"]})
        improvements.append({
            "check": "signing_identity_expiring_soon", "severity": "critical", "profiles": expiring_profiles,
        })

    os_by_profile = {profile: detect_os(curr_builds, profile) for profile in top_profiles}
    outliers = []
    for row in duration_rows:
        profile = row["profile"]
        os_code = os_by_profile.get(profile)
        if os_code is None:
            continue
        other_p50s = [r["p50"] for r in duration_rows if r["profile"] != profile and os_by_profile.get(r["profile"]) == os_code]
        if not other_p50s:
            continue
        if row["p50"] > 2 * mean(other_p50s):
            outliers.append(profile)
    if outliers:
        improvements.append({"check": "outlier_build_duration", "severity": "critical", "profiles": sorted(outliers)})

    script_profiles = sorted({
        issue["profile"] for issue in workflow_quality_issues if issue["check"] == "custom_script_not_from_git"
    })
    if script_profiles:
        improvements.append({"check": "custom_script_not_from_git", "severity": "advisory", "profiles": script_profiles})

    # Flags only profiles confirmed unconfigured; `None` (unresolved) is excluded.
    pr_missing = sorted(p for p in top_profiles if pr_configured_by_profile.get(p) is False)
    if pr_missing:
        improvements.append({"check": "pr_workflow_not_configured", "severity": "advisory", "profiles": pr_missing})

    versioning_profiles = sorted({
        issue["profile"] for issue in workflow_quality_issues if issue["check"] == "versioning_not_automated"
    })
    if versioning_profiles:
        improvements.append({"check": "versioning_not_automated", "severity": "advisory", "profiles": versioning_profiles})

    if security and security["profiles_without_env_vars"]:
        improvements.append({
            "check": "environment_variables_not_configured",
            "severity": "advisory",
            "profiles": security["profiles_without_env_vars"],
        })

    return improvements
