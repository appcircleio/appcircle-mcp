"""Get build insights report tool."""

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response
from .build_insights import artifact_health as ah
from .build_insights import health_snapshot as hs
from .build_insights import maturity_assessment as ma
from .build_insights import profile_configuration as pc
from .build_insights import queue_time as qt
from .build_insights import root_cause as rc
from .build_insights import workflow_quality as wq
from .build_insights import workflow_yaml as wy
from .build_insights.fetch import (
    fetch_all_build_history,
    fetch_all_build_profiles,
    fetch_all_queue_waiting,
    fetch_certificates,
    fetch_keystores,
    fetch_provisioning_profiles,
)

TOOL_NAME = "get_build_insights_report"
ALLOWED_SECTIONS = {
    "health_snapshot", "root_cause", "artifact_health", "workflow_quality", "queue_time", "maturity_assessment",
}
DEFAULT_PERIOD_DAYS = 30


def _normalize_sections(sections: Optional[List[str]]) -> set:
    if sections is None:
        return set(ALLOWED_SECTIONS)
    normalized = {s.strip() for s in sections if s and s.strip()}
    invalid = normalized - ALLOWED_SECTIONS
    if invalid:
        raise ValueError(
            f"Invalid section(s): {sorted(invalid)}. Valid sections: {sorted(ALLOWED_SECTIONS)}."
        )
    if not normalized:
        raise ValueError(f"No valid sections specified. Valid sections: {sorted(ALLOWED_SECTIONS)}.")
    return normalized


def _resolve_period(start_date: Optional[str], end_date: Optional[str]) -> tuple:
    """Both omitted -> last 30 days. Only one given -> fill the other to a
    30-day-wide window. Both given -> used exactly as provided."""
    if start_date is None and end_date is None:
        end = date.today()
        return end - timedelta(days=DEFAULT_PERIOD_DAYS), end
    if end_date is None:
        start = date.fromisoformat(start_date)
        return start, min(start + timedelta(days=DEFAULT_PERIOD_DAYS), date.today())
    if start_date is None:
        end = date.fromisoformat(end_date)
        return end - timedelta(days=DEFAULT_PERIOD_DAYS), end
    return date.fromisoformat(start_date), date.fromisoformat(end_date)


def _previous_period(current_start: date, current_end: date) -> tuple:
    """Same duration as the current period, immediately preceding it, no gap."""
    duration_days = (current_end - current_start).days + 1
    previous_end = current_start - timedelta(days=1)
    return previous_end - timedelta(days=duration_days - 1), previous_end


async def _soft_fetch(label: str, coro: Any, default: Any, failed_fetches: List[str]) -> Any:
    """Await `coro`; on any exception (HTTP error, timeout, connection error),
    log a warning, record `label` in `failed_fetches`, and return `default`
    instead of propagating."""
    try:
        return await coro
    except Exception as e:
        logger.warning(f"Optional fetch '{label}' failed, treating as unavailable: {e}")
        failed_fetches.append(label)
        return default


@mcp.tool()
async def get_build_insights_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sections: Optional[List[str]] = None,
    include_sub_orgs: bool = False,
) -> Dict[str, Any]:
    """
    Get a computed Build Insights Report over build history: Health Snapshot +
    Trends, Root Cause, Artifact Health, Workflow Quality, Queue Time, and
    Maturity Assessment analysis, aggregated server-side.

    Unlike get_build_history_report (which returns raw paginated records), this
    tool fetches every page internally, computes percentiles/grouping/MTTR/flaky
    detection in Python, and returns only the small aggregated result. Sections
    that can't be computed from the available data (e.g. a field stripped by an
    Appcircle role restriction) are omitted rather than rendered as zeros or
    fabricated, and flagged in meta.omitted_sections / meta.omitted_subsections.
    Only the current-period build history fetch is mandatory -- every other
    fetch (previous period, profiles, queue waiting, signing identities,
    per-profile workflow/trigger/configuration data) is best-effort: a 401/403
    from a token lacking permission for that specific resource (e.g. an
    admin-only endpoint) omits just the dependent section/subsection instead
    of failing the whole call, and is listed in meta.failed_fetches.

    A main-org access token sees build history spanning every sub-organization,
    but can only enumerate its own org's profiles (the Appcircle API itself
    enforces this -- not something this tool can fetch around). By default
    the report is scoped to the token's own organization: build records whose
    profile isn't in that token's own profile list are excluded before any
    section is computed, so every section always means the same scope. Set
    include_sub_orgs=True to keep cross-org records in history-derived
    metrics (Health Snapshot, Root Cause, Artifact Health, Speed/Reliability) --
    Workflow Quality/Discipline/Security for those profiles still can't be
    resolved (the API limitation doesn't go away), so they're omitted for
    those specific profiles rather than fabricated, and listed in
    meta.unresolved_profiles. queue_time has no profile field to scope by, so
    it's always a tree-wide aggregate regardless of this flag.

    Args:
        start_date: Optional start date (format: "YYYY-MM-DD") for the current period.
        end_date: Optional end date (format: "YYYY-MM-DD") for the current period.
                  If both start_date and end_date are omitted, defaults to the last 30 days.
                  If only one is given, the other is filled to a 30-day-wide window.
        sections: Optional list of sections to compute. Subset of
                  ["health_snapshot", "root_cause", "artifact_health", "workflow_quality",
                  "queue_time", "maturity_assessment"]. Defaults to all six. Invalid section
                  names return a validation error.
        include_sub_orgs: If True, keep cross-org build records in history-derived
                  metrics instead of filtering them to the token's own org (default
                  False). See the note above on what stays unresolved either way.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (date_range, sections.health_snapshot,
          sections.root_cause, sections.artifact_health, sections.workflow_quality,
          sections.queue_time, sections.maturity_assessment),
          meta (requested_sections, omitted_sections, omitted_subsections,
          failed_fetches, cross_org_builds_excluded, unresolved_profiles).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Full report, last 30 days: get_build_insights_report()
        Root cause only, custom range: get_build_insights_report(
            start_date="2026-01-01", end_date="2026-01-31", sections=["root_cause"]
        )
        Include cross-org records from a main-org token: get_build_insights_report(include_sub_orgs=True)
    """
    try:
        requested_sections = _normalize_sections(sections)
        current_start, current_end = _resolve_period(start_date, end_date)
        previous_start, previous_end = _previous_period(current_start, current_end)
        needs_health_snapshot = "health_snapshot" in requested_sections
        needs_artifact_health = "artifact_health" in requested_sections
        needs_workflow_quality = "workflow_quality" in requested_sections
        needs_queue_time = "queue_time" in requested_sections
        needs_maturity_assessment = "maturity_assessment" in requested_sections
        needs_root_cause = "root_cause" in requested_sections
        # True if either section needs workflow-YAML scoring fetched and computed.
        needs_workflow_scoring = needs_workflow_quality or needs_maturity_assessment
        needs_previous_period = needs_health_snapshot or needs_artifact_health or needs_maturity_assessment
        # Sections that consume curr_builds and so need the own-org scope filter applied.
        # queue_time has no profile field to scope by, so it's exempt.
        needs_history_driven = needs_health_snapshot or needs_artifact_health or needs_workflow_scoring or needs_root_cause
        needs_scope_filter = needs_history_driven and not include_sub_orgs
        needs_profiles = needs_health_snapshot or needs_workflow_scoring or needs_scope_filter

        failed_fetches: List[str] = []

        async with ApiClient() as api_client:
            current_task = fetch_all_build_history(
                api_client,
                start_date=current_start.isoformat(),
                end_date=current_end.isoformat(),
            )

            # Each fetch below is wrapped via _soft_fetch, degrading to a default
            # value on failure instead of raising out of the gather.
            optional_tasks: Dict[str, Any] = {}
            if needs_previous_period:
                optional_tasks["previous"] = _soft_fetch(
                    "previous_period",
                    fetch_all_build_history(
                        api_client,
                        start_date=previous_start.isoformat(),
                        end_date=previous_end.isoformat(),
                    ),
                    [],
                    failed_fetches,
                )
            if needs_profiles:
                optional_tasks["profiles"] = _soft_fetch(
                    "profiles",
                    fetch_all_build_profiles(api_client),
                    None,
                    failed_fetches,
                )
            if needs_queue_time:
                optional_tasks["queue_waiting"] = _soft_fetch(
                    "queue_waiting",
                    fetch_all_queue_waiting(
                        api_client,
                        start_date=current_start.isoformat(),
                        end_date=current_end.isoformat(),
                    ),
                    {"records": [], "summary": None},
                    failed_fetches,
                )
            if needs_maturity_assessment:
                optional_tasks["certificates"] = _soft_fetch(
                    "certificates", fetch_certificates(api_client), None, failed_fetches
                )
                optional_tasks["provisioning_profiles"] = _soft_fetch(
                    "provisioning_profiles", fetch_provisioning_profiles(api_client), None, failed_fetches
                )
                optional_tasks["keystores"] = _soft_fetch(
                    "keystores", fetch_keystores(api_client), None, failed_fetches
                )

            current_result, *optional_results = await asyncio.gather(current_task, *optional_tasks.values())
            results = {"current": current_result, **dict(zip(optional_tasks.keys(), optional_results))}

        curr_builds = results["current"]
        prev_builds = results.get("previous") or []
        all_profiles = results.get("profiles")  # None if not requested OR fetch failed; [] if genuinely empty
        queue_result = results.get("queue_waiting") or {"records": [], "summary": None}
        queue_builds = queue_result["records"]
        queue_plan_summary = queue_result["summary"]

        cross_org_builds_excluded = 0
        if needs_scope_filter:
            if all_profiles is None:
                # Profiles fetch failed; the own-org boundary can't be established,
                # so history is dropped (flows into the existing `if not curr_builds` omission paths).
                curr_builds, prev_builds = [], []
            else:
                own_profile_names = {p["name"] for p in all_profiles if p.get("name")}
                filtered_curr = [b for b in curr_builds if b.get("buildProfileName") in own_profile_names]
                cross_org_builds_excluded = len(curr_builds) - len(filtered_curr)
                curr_builds = filtered_curr
                prev_builds = [b for b in prev_builds if b.get("buildProfileName") in own_profile_names]

        data: Dict[str, Any] = {
            "date_range": {
                "current_start": current_start.isoformat(),
                "current_end": current_end.isoformat(),
                "previous_start": previous_start.isoformat(),
                "previous_end": previous_end.isoformat(),
            },
            "sections": {},
        }
        omitted_sections: List[str] = []
        omitted_subsections: List[str] = []

        # Shared by health_snapshot, artifact_health, and workflow scoring -- computed once, no extra fetch.
        top_profile_rows: List[Dict[str, Any]] = []
        if curr_builds and (needs_health_snapshot or needs_artifact_health or needs_workflow_scoring):
            top_profile_rows = hs.top_active_profiles(curr_builds, limit=5)
        top_profile_names = [row["profile"] for row in top_profile_rows]

        # Per-profile build-duration percentiles, shared by health_snapshot's
        # trends and maturity_assessment's Speed score -- computed once.
        duration_rows: List[Dict[str, Any]] = []
        if curr_builds and (needs_health_snapshot or needs_maturity_assessment):
            duration_rows = hs.per_profile_duration(curr_builds, prev_builds, top_profile_names)

        # Workflow YAML + trigger-config fetch, shared by workflow scoring and
        # maturity assessment: one shared connection, concurrent across the
        # top-5 profiles needing it. Trigger-config is fetched first since
        # fetch_profile_workflow_yaml uses it as a Push/PR identity fallback,
        # and maturity assessment's "PR workflow configured" check reads it directly.
        workflow_yaml_by_profile: Dict[str, Any] = {}
        triggers_by_profile: Dict[str, Any] = {}
        configs_by_profile: Dict[str, Any] = {}
        profile_id_by_name: Dict[str, str] = {}
        resolved_profiles: List[str] = []
        if needs_workflow_scoring and top_profile_names:
            profile_id_by_name = {p["name"]: p["id"] for p in (all_profiles or []) if p.get("name") and p.get("id")}
            resolved_profiles = [p for p in top_profile_names if p in profile_id_by_name]
            if resolved_profiles:
                async with ApiClient() as workflow_api_client:
                    fetched_triggers = await asyncio.gather(*[
                        _soft_fetch(
                            f"triggers:{profile}",
                            wy.fetch_profile_triggers(workflow_api_client, profile_id_by_name[profile]),
                            None,
                            failed_fetches,
                        )
                        for profile in resolved_profiles
                    ])
                    triggers_by_profile = dict(zip(resolved_profiles, fetched_triggers))

                    workflow_yaml_calls = asyncio.gather(*[
                        _soft_fetch(
                            f"workflow_yaml:{profile}",
                            wy.fetch_profile_workflow_yaml(
                                workflow_api_client, curr_builds, profile, profile_id_by_name[profile],
                                triggers_by_profile.get(profile),
                            ),
                            (None, None),
                            failed_fetches,
                        )
                        for profile in resolved_profiles
                    ])
                    if needs_maturity_assessment:
                        config_calls = asyncio.gather(*[
                            _soft_fetch(
                                f"configuration:{profile}",
                                pc.fetch_profile_configuration(
                                    workflow_api_client, curr_builds, profile, profile_id_by_name[profile]
                                ),
                                None,
                                failed_fetches,
                            )
                            for profile in resolved_profiles
                        ])
                        fetched_workflows, fetched_configs = await asyncio.gather(workflow_yaml_calls, config_calls)
                        configs_by_profile = dict(zip(resolved_profiles, fetched_configs))
                    else:
                        fetched_workflows = await workflow_yaml_calls
                workflow_yaml_by_profile = dict(zip(resolved_profiles, fetched_workflows))

        if needs_health_snapshot:
            if not curr_builds:
                omitted_sections.append("health_snapshot")
            else:
                top_triggers = hs.top_triggers(curr_builds)
                if top_triggers is None:
                    omitted_subsections.append("health_snapshot.top_triggers")

                if all_profiles is None:
                    omitted_subsections.append("health_snapshot.inactive_profiles")
                    inactive_profiles_result = None
                else:
                    inactive_profiles_result = hs.inactive_profiles(all_profiles, current_end)

                data["sections"]["health_snapshot"] = {
                    "summary": hs.compute_summary(curr_builds, prev_builds),
                    "top_active_profiles": top_profile_rows,
                    "inactive_profiles": inactive_profiles_result,
                    "top_build_activity": hs.top_build_activity(curr_builds, limit=5),
                    "top_triggers": top_triggers,
                    "trends": {
                        "daily_series": hs.daily_series(curr_builds, current_start, current_end),
                        "per_profile_duration": duration_rows,
                        "per_profile_duration_series": hs.per_profile_duration_series(
                            curr_builds, current_start, current_end, top_profile_names
                        ),
                    },
                }

        if needs_artifact_health:
            if not curr_builds:
                omitted_sections.append("artifact_health")
            else:
                per_profile_rows = ah.artifact_size_per_profile(curr_builds, prev_builds, top_profile_names)
                grower_shrinker = ah.biggest_grower_and_shrinker(per_profile_rows)
                data["sections"]["artifact_health"] = {
                    "artifact_size_per_profile": per_profile_rows,
                    "biggest_grower": grower_shrinker["grower"],
                    "biggest_shrinker": grower_shrinker["shrinker"],
                }

        # Per-profile workflow scoring, shared by workflow_quality's output
        # and maturity_assessment's Discipline score.
        per_profile_quality: List[Dict[str, Any]] = []
        workflow_quality_issues: List[Dict[str, Any]] = []
        if needs_workflow_scoring and curr_builds:
            for profile in top_profile_names:
                os_code = wq.detect_os(curr_builds, profile)
                push_workflow, pr_workflow = workflow_yaml_by_profile.get(profile, (None, None))

                push_score = wq.score_workflow(push_workflow["steps"], os_code, is_push=True) if push_workflow else None
                pr_score = wq.score_workflow(pr_workflow["steps"], os_code, is_push=False) if pr_workflow else None

                per_profile_quality.append({
                    "profile": profile,
                    "os": os_code,
                    "push": {"workflow_name": push_workflow["workflow_name"], **push_score} if push_score else None,
                    "pr": {"workflow_name": pr_workflow["workflow_name"], **pr_score} if pr_score else None,
                })

                workflow_quality_issues.extend(wq.best_practice_checks(
                    profile,
                    os_code,
                    push_workflow["workflow_name"] if push_workflow else None,
                    push_workflow["steps"] if push_workflow else None,
                    pr_workflow["workflow_name"] if pr_workflow else None,
                    pr_workflow["steps"] if pr_workflow else None,
                ))

        if needs_workflow_quality:
            # Omitted when there are no builds, or when every top profile's push/pr came back null.
            if not any(row["push"] or row["pr"] for row in per_profile_quality):
                omitted_sections.append("workflow_quality")
            else:
                data["sections"]["workflow_quality"] = {
                    "per_profile": per_profile_quality,
                    "best_practice_issues": workflow_quality_issues,
                }

        if needs_maturity_assessment:
            if not curr_builds:
                omitted_sections.append("maturity_assessment")
            else:
                # `None` means the profile's triggers fetch failed or its ID never
                # resolved -- distinct from a confirmed no-PR-settings result.
                pr_configured_by_profile = {
                    profile: (
                        None if (profile not in profile_id_by_name or f"triggers:{profile}" in failed_fetches)
                        else wy.has_pr_workflow_configured(triggers_by_profile.get(profile))
                    )
                    for profile in top_profile_names
                }

                reliability = ma.reliability_score(curr_builds, top_profile_names)
                if reliability["factors"]["warning_hotspots"] is None:
                    omitted_subsections.append("maturity_assessment.reliability.warning_hotspots")

                discipline = ma.discipline_score(
                    per_profile_quality, workflow_quality_issues, pr_configured_by_profile, top_profile_names
                )
                if discipline is None:
                    omitted_subsections.append("maturity_assessment.discipline")

                speed = ma.speed_score(duration_rows, top_profile_rows)
                if speed is None:
                    omitted_subsections.append("maturity_assessment.speed")

                security = ma.security_score(
                    configs_by_profile,
                    top_profile_names,
                    results.get("certificates"),
                    results.get("provisioning_profiles"),
                    results.get("keystores"),
                    datetime.now(timezone.utc),
                )
                if security is None:
                    omitted_subsections.append("maturity_assessment.security")

                overall = ma.combine_overall_score(
                    reliability["score"],
                    discipline["score"] if discipline else None,
                    speed["score"] if speed else None,
                    security["score"] if security else None,
                )

                # Reliability and Speed are recomputed against the previous period
                # using the same top-5 profile list. Discipline is reused unchanged.
                previous_overall_score: Optional[int] = None
                if prev_builds:
                    prev_reliability = ma.reliability_score(prev_builds, top_profile_names)
                    prev_duration_rows = hs.per_profile_duration(prev_builds, [], top_profile_names)
                    prev_build_count_by_profile = {
                        p: sum(1 for b in prev_builds if b["buildProfileName"] == p) for p in top_profile_names
                    }
                    prev_top_profile_rows = [
                        {"profile": p, "build_count": c} for p, c in prev_build_count_by_profile.items()
                    ]
                    prev_speed = ma.speed_score(prev_duration_rows, prev_top_profile_rows)
                    # Security is reused unchanged for both periods -- signing expiry
                    # is evaluated against wall-clock "now," not the historical period.
                    previous_overall = ma.combine_overall_score(
                        prev_reliability["score"],
                        discipline["score"] if discipline else None,
                        prev_speed["score"] if prev_speed else None,
                        security["score"] if security else None,
                    )
                    previous_overall_score = previous_overall["overall_score"]

                data["sections"]["maturity_assessment"] = {
                    "overall_score": overall["overall_score"],
                    "label": overall["label"],
                    "previous_overall_score": previous_overall_score,
                    "reliability": reliability,
                    "discipline": discipline,
                    "speed": speed,
                    "security": security,
                    "top_improvements": ma.top_improvements(
                        curr_builds, top_profile_names, duration_rows, workflow_quality_issues,
                        pr_configured_by_profile, security,
                    ),
                }

        if needs_queue_time:
            queue_summary = qt.compute_queue_wait_summary(queue_builds)
            if queue_summary is None:
                omitted_sections.append("queue_time")
            else:
                plan_breakdown = qt.plan_wait_breakdown(queue_plan_summary)
                if plan_breakdown is None:
                    omitted_subsections.append("queue_time.plan_breakdown")

                data["sections"]["queue_time"] = {
                    **queue_summary,
                    "daily_trend": qt.daily_queue_wait_trend(queue_builds),
                    "plan_breakdown": plan_breakdown,
                }

        if needs_root_cause:
            if not curr_builds:
                omitted_sections.append("root_cause")
            else:
                top_failing_steps = rc.top_failing_steps(curr_builds)
                if top_failing_steps is None:
                    omitted_subsections.append("root_cause.top_failing_steps")

                flaky = rc.flaky_cards(curr_builds)
                if flaky is None:
                    omitted_subsections.append("root_cause.flaky")

                warning_hotspots = rc.warning_hotspot_cards(curr_builds)
                if warning_hotspots is None:
                    omitted_subsections.append("root_cause.warning_hotspots")

                zero_success_workflows = rc.zero_success_workflow_cards(curr_builds)
                if zero_success_workflows is None:
                    omitted_subsections.append("root_cause.zero_success_workflows")

                data["sections"]["root_cause"] = {
                    "top_failing_steps": top_failing_steps,
                    "mttr": rc.mttr_cards(curr_builds),
                    "flaky": flaky,
                    "warning_hotspots": warning_hotspots,
                    "zero_success_workflows": zero_success_workflows,
                }

        # Empty unless workflow scoring was requested, since profile-ID resolution
        # only happens in that path.
        unresolved_profiles = (
            [p for p in top_profile_names if p not in profile_id_by_name] if needs_workflow_scoring else []
        )

        meta = {
            "requested_sections": sorted(requested_sections),
            "omitted_sections": omitted_sections,
            "omitted_subsections": omitted_subsections,
            "failed_fetches": failed_fetches,
            "cross_org_builds_excluded": cross_org_builds_excluded,
            "unresolved_profiles": unresolved_profiles,
        }

        logger.info(
            f"Successfully computed build insights report for sections {sorted(requested_sections)} "
            f"({current_start.isoformat()} to {current_end.isoformat()})"
        )
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to get build insights report: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
