"""Unit tests for get_build_insights_report (respx-mocked)."""

import re
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import Response

from src.tools.report.get_build_insights_report import get_build_insights_report


def _mock_empty_signing_identities(mocked_api):
    """maturity_assessment unconditionally fetches all three signing-identity
    lists org-wide; mock them empty for tests that don't exercise Security
    specifically, so no real network call is attempted."""
    mocked_api.get("/signing-identity/v2/certificates").mock(return_value=Response(200, json=[]))
    mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(return_value=Response(200, json=[]))
    mocked_api.get("/signing-identity/v2/keystores").mock(return_value=Response(200, json=[]))

# Matches /build/v1/profiles/{any-id}/triggers -- the maturity_assessment
# trigger-config fetch, which fires per resolved top-5 profile regardless of
# build-history activity (unlike the workflow-YAML fetch).
TRIGGERS_URL_PATTERN = re.compile(r"/build/v1/profiles/[^/]+/triggers$")
EMPTY_TRIGGERS_RESPONSE = {"pullRequestSettings": [], "pushSettings": [], "tagSettings": []}

FULL_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 4, "enablePrevious": False, "enableNext": False},
    "data": [
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 4.0,
            "failedStep": None, "hasWarning": False, "workflowName": "Default Push Workflow",
            "commitId": "abc1234", "triggerCategory": 0, "initiatedBy": "dev@example.com", "os": 1,
            "targetFile": {"filename": "app.ipa", "fileSize": 40.0},
        },
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 1,
            "buildStartDate": "2026-01-06T10:00:00Z", "buildDuration": 0.5,
            "failedStep": "Xcodebuild for Devices", "hasWarning": True, "workflowName": "Default Push Workflow",
            "commitId": "def5678", "triggerCategory": 0, "initiatedBy": "dev@example.com", "os": 1,
        },
        {
            "buildProfileName": "Android Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2026-01-06T11:00:00Z", "buildDuration": 3.0,
            "failedStep": None, "hasWarning": False, "workflowName": "Default Push Workflow",
            "commitId": "ghi9012", "triggerCategory": 0, "initiatedBy": "ci-bot", "os": 2,
            "targetFile": {"filename": "app.aab", "fileSize": 20.0},
        },
        {
            "buildProfileName": "Android Build", "branchName": "main", "buildStatus": 1,
            "buildStartDate": "2026-01-07T11:00:00Z", "buildDuration": 0.4,
            "failedStep": "Gradle Build", "hasWarning": False, "workflowName": "Default Push Workflow",
            "commitId": "jkl3456", "triggerCategory": 0, "initiatedBy": "ci-bot", "os": 2,
        },
    ],
}
# All four records above are triggerCategory=0 (Manual) on purpose: tests in
# this file that don't care about Workflow Quality specifically must not
# accidentally resolve a Push/PR workflow identity (triggerCategory 1/2),
# which would trigger an unmocked workflow-YAML fetch. See
# WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE below for that dedicated case.

WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 2, "enablePrevious": False, "enableNext": False},
    "data": [
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 4.0,
            "workflowName": "Default Push Workflow", "triggerCategory": 2, "os": 1,
        },
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2026-01-06T10:00:00Z", "buildDuration": 4.0,
            "workflowName": "Default PR Workflow", "triggerCategory": 1, "os": 1,
        },
    ],
}

WORKFLOW_QUALITY_PROFILES_RESPONSE = [
    {"id": "p1", "name": "iOS Build", "lastBuildDate": "2026-01-06T10:00:00Z"},
]

# Same shape as WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE but with
# configurationName present, so resolve_configuration_name resolves and the
# Security path's configuration list/detail fetches actually fire.
SECURITY_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 1, "enablePrevious": False, "enableNext": False},
    "data": [
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 4.0,
            "workflowName": "Default Push Workflow", "triggerCategory": 2, "os": 1,
            "configurationName": "Default Configuration",
        },
    ],
}

# A main-org token's build history: "Main Org Build" is its own profile,
# "Sub Org Build" bleeds in from a sub-org the token can see history for but
# can't enumerate profiles for. "Sub Org Build" has more builds, so it would
# win the #1 top-active-profile spot if not filtered out by default.
MIXED_ORG_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 3, "enablePrevious": False, "enableNext": False},
    "data": [
        {"buildProfileName": "Main Org Build", "branchName": "main", "buildStatus": 0,
         "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 5.0,
         "workflowName": "Default Push Workflow", "triggerCategory": 2, "os": 1},
        {"buildProfileName": "Sub Org Build", "branchName": "main", "buildStatus": 0,
         "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 50.0,
         "workflowName": "Push WF", "triggerCategory": 2, "os": 1},
        {"buildProfileName": "Sub Org Build", "branchName": "main", "buildStatus": 0,
         "buildStartDate": "2026-01-06T10:00:00Z", "buildDuration": 51.0,
         "workflowName": "Push WF", "triggerCategory": 2, "os": 1},
    ],
}

# Main-org token's own profile list -- "Sub Org Build" is genuinely absent,
# not an error (the API enforces this boundary).
MAIN_ORG_PROFILES_RESPONSE = [
    {"id": "p1", "name": "Main Org Build", "lastBuildDate": "2026-01-05T10:00:00Z"},
]

WORKFLOW_QUALITY_WORKFLOW_LIST_RESPONSE = [
    {"id": "push-id", "workflowName": "Default Push Workflow"},
    {"id": "pr-id", "workflowName": "Default PR Workflow"},
]

WORKFLOW_QUALITY_PUSH_YAML = """
steps:
  - componentType: appcircle_git_clone
    enabled: true
  - componentType: appcircle_cocoapods
    enabled: true
  - componentType: appcircle_ios_build_sign
    enabled: true
  - componentType: appcircle_export_build_artifacts
    enabled: true
  - componentType: appcircle_custom_script
    enabled: true
"""

WORKFLOW_QUALITY_PR_YAML = """
steps:
  - componentType: appcircle_git_clone
    enabled: true
"""

QUEUE_WAITING_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 4, "enablePrevious": False, "enableNext": False},
    "data": [
        {"buildStatus": 0, "buildStartDate": "2026-06-22T11:56:18.12Z", "buildDuration": 1.0},
        {"buildStatus": 2, "buildStartDate": "2026-06-17T17:26:15.756Z", "buildDuration": 1.0},
        {"buildStatus": 2, "buildStartDate": "2026-06-17T17:25:03.941Z", "buildDuration": 1.0},
        {"buildStatus": 0, "buildStartDate": "2026-06-17T10:34:48.409Z", "buildDuration": 1.0},
    ],
    "summary": {"totalBuildsRun": 4, "totalBuildWaitingDuration": 4.0, "standard": 0.0, "velocity": 4.0, "ultra": 0.0},
}

EMPTY_QUEUE_WAITING_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 0, "enablePrevious": False, "enableNext": False},
    "data": [],
}

MINIMAL_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 1, "enablePrevious": False, "enableNext": False},
    "data": [
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 1,
            "buildStartDate": "2026-01-06T10:00:00Z", "buildDuration": 0.5,
        },
    ],
}

PREV_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 1, "enablePrevious": False, "enableNext": False},
    "data": [
        {
            "buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
            "buildStartDate": "2025-12-05T10:00:00Z", "buildDuration": 4.0,
            "targetFile": {"filename": "app.ipa", "fileSize": 30.0},
        },
    ],
}

EMPTY_BUILD_HISTORY_RESPONSE = {
    "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 0, "enablePrevious": False, "enableNext": False},
    "data": [],
}

SAMPLE_PROFILES_RESPONSE = [
    {"id": "1", "name": "iOS Build", "lastBuildDate": "2026-01-06T10:00:00Z"},
    {"id": "2", "name": "Android Build", "lastBuildDate": "2026-01-07T11:00:00Z"},
    {"id": "3", "name": "Stale Profile", "lastBuildDate": "2025-01-01T00:00:00Z"},
]


@pytest.mark.asyncio
class TestGetBuildInsightsReportSuccess:
    async def test_full_report_envelope_shape(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=QUEUE_WAITING_RESPONSE))
        mocked_api.get(TRIGGERS_URL_PATTERN).mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        assert "health_snapshot" in result["data"]["sections"]
        assert "root_cause" in result["data"]["sections"]
        assert "artifact_health" in result["data"]["sections"]
        assert "queue_time" in result["data"]["sections"]
        assert "maturity_assessment" in result["data"]["sections"]
        assert result["meta"]["requested_sections"] == [
            "artifact_health", "health_snapshot", "maturity_assessment", "queue_time", "root_cause", "workflow_quality",
        ]
        # All triggerCategory=0 (Manual) in this fixture and triggers are
        # mocked empty too, so no Push/PR workflow identity resolves for any
        # profile -- workflow_quality has nothing real to report and is
        # omitted, not rendered as an all-null skeleton.
        assert result["meta"]["omitted_sections"] == ["workflow_quality"]
        # Discipline can't be computed without any resolved workflow either --
        # omitted, not fabricated. No build record carries configurationName,
        # so Security can't be resolved this period -- also omitted.
        assert result["meta"]["omitted_subsections"] == ["maturity_assessment.discipline", "maturity_assessment.security"]
        assert result["data"]["sections"]["health_snapshot"]["summary"]["current"]["total"] == 4
        assert len(result["data"]["sections"]["root_cause"]["mttr"]) >= 0
        assert result["data"]["sections"]["queue_time"]["total_wait_minutes"] == 4.0
        maturity = result["data"]["sections"]["maturity_assessment"]
        assert maturity["discipline"] is None
        assert maturity["security"] is None
        assert isinstance(maturity["overall_score"], int)
        assert maturity["label"] in {"Optimizing", "Advancing", "Practicing", "Developing"}
        # Discipline and Security both missing -> renormalized across just
        # Reliability (0.30) and Speed (0.15), which preserves the same 2:1
        # ratio as the legacy reliability*0.667 + speed*0.333 fallback.
        assert maturity["overall_score"] == round(
            maturity["reliability"]["score"] * 0.667 + maturity["speed"]["score"] * 0.333
        )

    async def test_artifact_health_only_fetches_previous_period_and_profiles_for_scoping(self, mocked_api):
        build_route = mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))

        result = await get_build_insights_report(
            sections=["artifact_health"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert "artifact_health" in result["data"]["sections"]
        assert "health_snapshot" not in result["data"]["sections"]
        # Now fetched even for artifact_health alone -- needed to establish
        # the own-org scope boundary before filtering curr_builds.
        assert len(profiles_route.calls) == 1
        assert len(build_route.calls) == 2  # current + previous period, needed for deltas

    async def test_artifact_health_grower_shrinker_end_to_end(self, mocked_api):
        def responder(request):
            if request.url.params.get("startDate") == "2026-01-01":
                return Response(200, json=FULL_BUILD_HISTORY_RESPONSE)
            return Response(200, json=PREV_BUILD_HISTORY_RESPONSE)

        mocked_api.get("/report/v2/build").mock(side_effect=responder)
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))

        result = await get_build_insights_report(
            sections=["artifact_health"], start_date="2026-01-01", end_date="2026-01-10"
        )

        artifact_section = result["data"]["sections"]["artifact_health"]
        ios_row = next(r for r in artifact_section["artifact_size_per_profile"] if r["profile"] == "iOS Build")
        assert ios_row["current_avg_size_mb"] == 40.0
        assert ios_row["prev_avg_size_mb"] == 30.0
        assert artifact_section["biggest_grower"]["profile"] == "iOS Build"

    async def test_root_cause_only_fetches_profiles_for_scoping_but_skips_previous_period(self, mocked_api):
        build_route = mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))

        result = await get_build_insights_report(sections=["root_cause"], start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        assert "root_cause" in result["data"]["sections"]
        assert "health_snapshot" not in result["data"]["sections"]
        # Now fetched even for root_cause alone -- needed to establish the
        # own-org scope boundary before filtering curr_builds.
        assert len(profiles_route.calls) == 1
        assert len(build_route.calls) == 1  # current period only, no previous period needed

    async def test_omits_subsections_when_optional_fields_missing(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=MINIMAL_BUILD_HISTORY_RESPONSE))
        # Must include "iOS Build" (the fixture's only profile) so the
        # own-org scope filter doesn't drop it -- this test is about
        # field-level omissions, not full-section omission from scoping.
        mocked_api.get("/build/v2/profiles").mock(
            return_value=Response(200, json=[{"id": "1", "name": "iOS Build", "lastBuildDate": "2026-01-06T10:00:00Z"}])
        )
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        omitted = set(result["meta"]["omitted_subsections"])
        assert omitted == {
            "health_snapshot.top_triggers",
            "root_cause.top_failing_steps",
            "root_cause.flaky",
            "root_cause.warning_hotspots",
            "root_cause.zero_success_workflows",
            "maturity_assessment.discipline",
            "maturity_assessment.speed",
            "maturity_assessment.reliability.warning_hotspots",
            "maturity_assessment.security",
        }
        # artifact_health has no field-presence-gated subsections -- it still
        # computes (as an empty list, since there's no targetFile/artifactItems
        # in this minimal fixture), rather than being omitted or erroring.
        assert result["data"]["sections"]["artifact_health"]["artifact_size_per_profile"] == []

    async def test_omits_sections_when_no_builds_in_period(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        assert set(result["meta"]["omitted_sections"]) == {
            "health_snapshot", "root_cause", "artifact_health", "workflow_quality", "queue_time", "maturity_assessment",
        }
        assert result["data"]["sections"] == {}

    async def test_defaults_to_last_30_days_when_no_dates_given(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report()

        expected_end = date.today()
        expected_start = expected_end - timedelta(days=30)
        assert result["data"]["date_range"]["current_start"] == expected_start.isoformat()
        assert result["data"]["date_range"]["current_end"] == expected_end.isoformat()

    async def test_only_start_date_given_fills_a_30_day_window(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01")

        assert result["data"]["date_range"]["current_start"] == "2026-01-01"
        assert result["data"]["date_range"]["current_end"] == "2026-01-31"

    async def test_only_end_date_given_fills_a_30_day_window(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(end_date="2026-01-31")

        assert result["data"]["date_range"]["current_start"] == "2026-01-01"
        assert result["data"]["date_range"]["current_end"] == "2026-01-31"

    async def test_queue_time_only_skips_previous_period_and_profiles(self, mocked_api):
        build_route = mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=QUEUE_WAITING_RESPONSE))

        result = await get_build_insights_report(
            sections=["queue_time"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert "queue_time" in result["data"]["sections"]
        assert len(profiles_route.calls) == 0
        assert len(build_route.calls) == 1  # current period only -- queue_time doesn't even use it

    async def test_queue_time_end_to_end_matches_real_example(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=QUEUE_WAITING_RESPONSE))

        result = await get_build_insights_report(
            sections=["queue_time"], start_date="2026-06-16", end_date="2026-06-23"
        )

        queue_section = result["data"]["sections"]["queue_time"]
        assert queue_section["total_wait_minutes"] == 4.0
        assert queue_section["avg_wait_minutes"] == 1.0
        assert queue_section["build_count"] == 4
        assert {pt["date"] for pt in queue_section["daily_trend"]} == {"2026-06-17", "2026-06-22"}
        assert queue_section["plan_breakdown"] == {
            "standard_wait_minutes": 0.0,
            "velocity_wait_minutes": 4.0,
            "ultra_wait_minutes": 0.0,
        }

    async def test_queue_time_plan_breakdown_omitted_when_summary_lacks_plan_fields(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json={
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 1, "enablePrevious": False, "enableNext": False},
            "data": [{"buildStatus": 0, "buildStartDate": "2026-06-17T10:34:48.409Z", "buildDuration": 1.0}],
            "summary": {"totalBuildsRun": 1, "totalBuildWaitingDuration": 1.0},
        }))

        result = await get_build_insights_report(
            sections=["queue_time"], start_date="2026-06-16", end_date="2026-06-23"
        )

        assert result["data"]["sections"]["queue_time"]["plan_breakdown"] is None
        assert "queue_time.plan_breakdown" in result["meta"]["omitted_subsections"]

    async def test_queue_time_omitted_when_no_valid_records(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))

        result = await get_build_insights_report(
            sections=["queue_time"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert "queue_time" not in result["data"]["sections"]
        assert "queue_time" in result["meta"]["omitted_sections"]

    async def test_workflow_quality_only_fetches_profiles_but_not_previous_period(self, mocked_api):
        build_route = mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=EMPTY_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[]))

        result = await get_build_insights_report(
            sections=["workflow_quality"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert len(profiles_route.calls) == 1  # needed to resolve profile IDs
        assert len(build_route.calls) == 1  # current period only, no previous period needed

    async def test_workflow_quality_end_to_end(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=WORKFLOW_QUALITY_PROFILES_RESPONSE))
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=WORKFLOW_QUALITY_WORKFLOW_LIST_RESPONSE)
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/pr-id").mock(
            return_value=Response(200, json={"workflowName": "Default PR Workflow", "workflowDocument": WORKFLOW_QUALITY_PR_YAML})
        )
        # Resolved entirely from build history here -- mocked empty so the
        # trigger-config fallback finds nothing and doesn't interfere.
        mocked_api.get(TRIGGERS_URL_PATTERN).mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))

        result = await get_build_insights_report(
            sections=["workflow_quality"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        entry = result["data"]["sections"]["workflow_quality"]["per_profile"][0]
        assert entry["profile"] == "iOS Build"
        assert entry["os"] == 1
        assert entry["push"]["workflow_name"] == "Default Push Workflow"
        assert entry["push"]["tier1_score"] == 60  # git_clone, cocoapods, ios_build_sign, export_build_artifacts all present
        assert entry["pr"]["workflow_name"] == "Default PR Workflow"
        assert entry["pr"]["tier1_score"] < 60  # only git_clone present

        issues = result["data"]["sections"]["workflow_quality"]["best_practice_issues"]
        assert any(i["check"] == "custom_script_not_from_git" and i["workflow"] == "Default Push Workflow" for i in issues)

    async def test_workflow_quality_omitted_when_no_profile_resolves_a_workflow(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))
        # No Push/PR workflow configured at all here either -- the
        # trigger-config fallback (see the dedicated all-manual test below)
        # also has nothing to resolve.
        triggers_route = mocked_api.get(TRIGGERS_URL_PATTERN).mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))

        result = await get_build_insights_report(
            sections=["workflow_quality"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        # Every top profile's push/pr come back null (no resolvable workflow
        # at all) -- an all-null per_profile skeleton carries no real content,
        # so the section is omitted rather than rendered hollow.
        assert "workflow_quality" not in result["data"]["sections"]
        assert result["meta"]["omitted_sections"] == ["workflow_quality"]
        # profiles were fetched (needed for IDs) and triggers were checked as
        # a fallback, but no workflow-list/detail calls happened since
        # neither build history nor trigger config resolves a Push/PR
        # workflow for these profiles in this fixture.
        assert len(profiles_route.calls) == 1
        assert len(triggers_route.calls) == 2  # one per top-5 profile (iOS Build, Android Build)
        workflow_calls = [c for c in mocked_api.calls if "/workflows/" in str(c.request.url)]
        assert workflow_calls == []

    async def test_workflow_quality_resolves_all_manual_profile_via_trigger_config(self, mocked_api):
        """The scenario this fallback exists for: a profile triggered only
        manually this period (every build is `triggerCategory=0`) has no
        Push/PR identity resolvable from build history at all, even though a
        Push/PR workflow is genuinely configured -- without the fallback,
        Workflow Quality (and Discipline) would render that profile as
        entirely null."""
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))
        mocked_api.get("/build/v1/profiles/1/triggers").mock(return_value=Response(200, json={
            "pullRequestSettings": [], "pushSettings": [{"workflowId": "push-id"}], "tagSettings": [],
        }))
        mocked_api.get("/build/v1/profiles/2/triggers").mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))
        mocked_api.get("/build/v2/profiles/1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )

        result = await get_build_insights_report(
            sections=["workflow_quality"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        # One profile resolved -- enough real content to keep the section,
        # unlike the fully-hollow case (every profile null) which omits it.
        assert "workflow_quality" not in result["meta"]["omitted_sections"]
        entries = {e["profile"]: e for e in result["data"]["sections"]["workflow_quality"]["per_profile"]}
        assert entries["iOS Build"]["push"]["workflow_name"] == "Default Push Workflow"
        assert entries["iOS Build"]["pr"] is None
        # Android Build's trigger config is empty too -- genuinely unconfigured.
        assert entries["Android Build"]["push"] is None
        assert entries["Android Build"]["pr"] is None
        # No workflow-list call needed -- the trigger config already gave the id directly.
        workflow_list_calls = [c for c in mocked_api.calls if str(c.request.url).endswith("/workflows/")]
        assert workflow_list_calls == []

    async def test_inactive_profiles_anchored_to_period_end_not_wall_clock_today(self, mocked_api):
        """`inactive_profiles` must read relative to the report's own period,
        not real wall-clock "today" -- otherwise a historical-period report
        (this one queries May 2025, long before whenever the test runs)
        would mark a profile inactive even though it built mid-period, which
        contradicts `top_active_profiles` reporting it as active."""
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[
            # Built mid-period (well within 30 days of current_end=2025-05-31) -- must read active.
            {"id": "1", "name": "iOS Build", "lastBuildDate": "2025-05-20T00:00:00Z"},
            # Stale even relative to current_end -- must read inactive either way.
            {"id": "2", "name": "Android Build", "lastBuildDate": "2025-01-01T00:00:00Z"},
        ]))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=EMPTY_QUEUE_WAITING_RESPONSE))
        mocked_api.get(TRIGGERS_URL_PATTERN).mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2025-05-01", end_date="2025-05-31")

        inactive = result["data"]["sections"]["health_snapshot"]["inactive_profiles"]
        assert [p["profile"] for p in inactive] == ["Android Build"]


@pytest.mark.asyncio
class TestMaturityAssessmentSection:
    def _mock_workflow_quality_fixture(self, mocked_api, pr_configured=True):
        build_route = mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE))
        profiles_route = mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=WORKFLOW_QUALITY_PROFILES_RESPONSE))
        workflow_list_route = mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=WORKFLOW_QUALITY_WORKFLOW_LIST_RESPONSE)
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/pr-id").mock(
            return_value=Response(200, json={"workflowName": "Default PR Workflow", "workflowDocument": WORKFLOW_QUALITY_PR_YAML})
        )
        triggers_route = mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={
                "pullRequestSettings": [{"workflowId": "pr-id"}] if pr_configured else [],
                "pushSettings": [{"workflowId": "push-id"}],
                "tagSettings": [],
            })
        )
        # WORKFLOW_QUALITY_BUILD_HISTORY_RESPONSE carries no configurationName,
        # so resolve_configuration_name short-circuits before any HTTP call --
        # the configurations list/detail endpoints are never hit for this
        # fixture, only the org-wide signing-identity lists need mocking.
        _mock_empty_signing_identities(mocked_api)
        return build_route, profiles_route, workflow_list_route, triggers_route

    async def test_only_section_still_fetches_workflow_scoring_triggers_and_previous_period(self, mocked_api):
        build_route, profiles_route, workflow_list_route, triggers_route = self._mock_workflow_quality_fixture(mocked_api)

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert "maturity_assessment" in result["data"]["sections"]
        assert "workflow_quality" not in result["data"]["sections"]
        assert len(profiles_route.calls) == 1
        assert len(workflow_list_route.calls) == 1  # workflow scoring fetched even though not rendered
        assert len(triggers_route.calls) == 1
        assert len(build_route.calls) == 2  # current + previous period, needed for the Reliability/Speed delta

    async def test_end_to_end_scoring_matches_hand_computed_values(self, mocked_api):
        self._mock_workflow_quality_fixture(mocked_api, pr_configured=True)

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        maturity = result["data"]["sections"]["maturity_assessment"]
        # Both builds succeed (status 0), no hasWarning/commitId field present
        # in the fixture -- warning_hotspots is omitted and the other 3
        # factors (success_rate, mttr, flaky) are each perfect.
        assert maturity["reliability"] == {
            "score": 100,
            "factors": {
                "success_rate": {"value": 1.0, "factor_score": 100},
                "mttr": {"value_hours": 0.0, "factor_score": 100},
                "flaky": {"count": 0, "factor_score": 100},
                "warning_hotspots": None,
            },
        }
        # Push workflow (60/100: tier1 only) + PR workflow (15/100: git_clone
        # only) -> wf_completeness = mean(60, 15) = 37.5 -> 38. Best-practice:
        # versioning missing on Push (0/1), inline custom script on Push
        # (0/1 "passing"), PR configured (1/1) -> bp = 0+0+33.33 -> 33.
        assert maturity["discipline"] == {"score": 35, "wf_completeness_score": 38, "bp_score": 33}
        # Both builds take 4.0 minutes (ratio 1.0 < 1.5) -> 100% consistent.
        assert maturity["speed"] == {"score": 100, "weighted_avg_ratio": 1.0, "consistency": "consistent"}
        # No build record carries configurationName -> Security can't be
        # resolved this period, omitted (not fabricated). With Security
        # missing, weights renormalize to exactly the legacy 40/40/20 split
        # (0.30/0.75, 0.30/0.75, 0.15/0.75).
        assert maturity["security"] is None
        assert maturity["overall_score"] == round(100 * 0.40 + 35 * 0.40 + 100 * 0.20)
        assert maturity["label"] == "Advancing"
        # Same build data both periods (single mock for both calls) -> the
        # delta is flat, confirming Discipline is reused unchanged.
        assert maturity["previous_overall_score"] == maturity["overall_score"]

        assert maturity["top_improvements"] == [
            {"check": "custom_script_not_from_git", "severity": "advisory", "profiles": ["iOS Build"]},
            {"check": "versioning_not_automated", "severity": "advisory", "profiles": ["iOS Build"]},
        ]

    async def test_pr_workflow_not_configured_surfaces_as_top_improvement(self, mocked_api):
        self._mock_workflow_quality_fixture(mocked_api, pr_configured=False)

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        top_improvements = result["data"]["sections"]["maturity_assessment"]["top_improvements"]
        assert {"check": "pr_workflow_not_configured", "severity": "advisory", "profiles": ["iOS Build"]} in top_improvements

    async def test_security_section_end_to_end_with_expiring_certificate(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=SECURITY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=WORKFLOW_QUALITY_PROFILES_RESPONSE))
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=WORKFLOW_QUALITY_WORKFLOW_LIST_RESPONSE)
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={"pullRequestSettings": [], "pushSettings": [{"workflowId": "push-id"}], "tagSettings": []})
        )
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[
                {"item1": {"id": "cfg-1", "configurationName": "Default Configuration"}, "item2": []},
            ])
        )
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(
            return_value=Response(200, json={
                "environmentVariables": [],
                "signingIdentities": [
                    {"signingIdentityType": 2, "entityId": "cert-1", "bundleIdentifier": None},
                ],
            })
        )
        near_expiry = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        mocked_api.get("/signing-identity/v2/certificates").mock(
            return_value=Response(200, json=[{"id": "cert-1", "name": "Expiring Cert", "expireDate": near_expiry}])
        )
        mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/signing-identity/v2/keystores").mock(return_value=Response(200, json=[]))

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        maturity = result["data"]["sections"]["maturity_assessment"]
        security = maturity["security"]
        assert security["signing_health_score"] == 0  # the only resolved identity is expiring within 30 days
        assert security["env_var_usage_score"] == 0  # no environment variables configured
        assert security["expiring_soon"][0]["id"] == "cert-1"
        assert security["expiring_soon"][0]["type"] == "certificate"
        assert security["expiring_soon"][0]["profiles"] == ["iOS Build"]
        assert security["profiles_without_env_vars"] == ["iOS Build"]
        assert isinstance(maturity["overall_score"], int)  # 4-weight formula now includes Security

        top_improvements = maturity["top_improvements"]
        assert {"check": "signing_identity_expiring_soon", "severity": "critical", "profiles": ["iOS Build"]} in top_improvements
        assert {"check": "environment_variables_not_configured", "severity": "advisory", "profiles": ["iOS Build"]} in top_improvements


@pytest.mark.asyncio
class TestSubOrgScoping:
    """A main-org token sees build history spanning every sub-org but can
    only enumerate its own org's profiles. By default, foreign-org records
    are filtered out before any section is computed; include_sub_orgs=True
    keeps them in history-derived metrics while relying on the tri-state
    unresolved-profile handling to avoid false signals."""

    async def test_default_mode_excludes_foreign_org_profile_from_every_section(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=MIXED_ORG_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=MAIN_ORG_PROFILES_RESPONSE))
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={"pullRequestSettings": [{"workflowId": "x"}], "pushSettings": [], "tagSettings": []})
        )
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        profiles_seen = {row["profile"] for row in result["data"]["sections"]["health_snapshot"]["top_active_profiles"]}
        assert profiles_seen == {"Main Org Build"}
        # 2 of the 3 fixture records belong to the foreign-org profile.
        assert result["meta"]["cross_org_builds_excluded"] == 2
        assert result["meta"]["unresolved_profiles"] == []
        top_improvements = result["data"]["sections"]["maturity_assessment"]["top_improvements"]
        assert not any("Sub Org Build" in i.get("profiles", []) for i in top_improvements)

    async def test_include_sub_orgs_keeps_history_metrics_but_never_falsely_flags_pr_check(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=MIXED_ORG_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=MAIN_ORG_PROFILES_RESPONSE))
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={"pullRequestSettings": [], "pushSettings": [{"workflowId": "x"}], "tagSettings": []})
        )
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10", include_sub_orgs=True
        )

        assert result["success"] is True
        assert result["meta"]["cross_org_builds_excluded"] == 0
        assert result["meta"]["unresolved_profiles"] == ["Sub Org Build"]
        # "Sub Org Build"'s triggers were never fetched (no profile ID to
        # fetch with), so it reads as unknown, not a confirmed "not configured" flag.
        top_improvements = result["data"]["sections"]["maturity_assessment"]["top_improvements"]
        assert not any(i["check"] == "pr_workflow_not_configured" and "Sub Org Build" in i["profiles"] for i in top_improvements)

    async def test_include_sub_orgs_with_profiles_fetch_failure_omits_inactive_profiles_only(self, mocked_api):
        # Under include_sub_orgs=True the scope filter never runs, so a denied
        # profiles fetch doesn't zero out curr_builds -- health_snapshot still
        # computes, with inactive_profiles omitted.
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=MIXED_ORG_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(403, json={"message": "Forbidden"}))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(
            sections=["health_snapshot"], start_date="2026-01-01", end_date="2026-01-10", include_sub_orgs=True
        )

        assert result["success"] is True
        assert result["data"]["sections"]["health_snapshot"]["inactive_profiles"] is None
        assert "health_snapshot.inactive_profiles" in result["meta"]["omitted_subsections"]
        assert result["data"]["sections"]["health_snapshot"]["summary"]["current"]["total"] == 3


@pytest.mark.asyncio
class TestGracefulDegradation:
    """A denied/failed endpoint (e.g. an admin-only resource on a non-admin
    token) must omit just the dependent section/subsection -- not crash the
    whole report -- and must never let "couldn't fetch" masquerade as a
    confirmed clean/dirty signal."""

    async def test_queue_waiting_403_omits_only_queue_time(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=SAMPLE_PROFILES_RESPONSE))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(403, json={"message": "Forbidden"}))
        mocked_api.get(TRIGGERS_URL_PATTERN).mock(return_value=Response(200, json=EMPTY_TRIGGERS_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        assert "queue_time" not in result["data"]["sections"]
        assert "queue_time" in result["meta"]["omitted_sections"]
        assert "queue_waiting" in result["meta"]["failed_fetches"]
        # Everything unrelated to queue-waiting is unaffected. workflow_quality
        # is *also* omitted here, but for an unrelated reason (this fixture's
        # all-manual builds + empty triggers resolve no Push/PR workflow for
        # any profile) -- not a side effect of the queue_waiting 403.
        assert "health_snapshot" in result["data"]["sections"]
        assert "root_cause" in result["data"]["sections"]
        assert "artifact_health" in result["data"]["sections"]
        assert "workflow_quality" in result["meta"]["omitted_sections"]
        assert "maturity_assessment" in result["data"]["sections"]

    async def test_profiles_403_omits_all_history_driven_sections_not_falsely_partial(self, mocked_api):
        # A denied profiles fetch means the own-org scope boundary can't be
        # established, so every history-driven section is omitted rather
        # than computed from a fabricated empty profiles list.
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=FULL_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(403, json={"message": "Forbidden"}))
        mocked_api.get("/report/v1/build/queue-waiting").mock(return_value=Response(200, json=QUEUE_WAITING_RESPONSE))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is True
        assert "profiles" in result["meta"]["failed_fetches"]
        assert set(result["meta"]["omitted_sections"]) == {
            "health_snapshot", "root_cause", "artifact_health", "workflow_quality", "maturity_assessment",
        }
        # queue_time has no profile dimension to scope by -- entirely
        # unaffected by the profiles fetch failing.
        assert "queue_time" in result["data"]["sections"]

    async def test_one_profiles_triggers_fetch_failing_does_not_flag_it_as_not_configured(self, mocked_api):
        two_profile_history = {
            "pagination": {"page": 1, "perPage": 100, "pageCount": 1, "totalCount": 2, "enablePrevious": False, "enableNext": False},
            "data": [
                {"buildProfileName": "iOS Build", "branchName": "main", "buildStatus": 0,
                 "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 4.0,
                 "workflowName": "Default Push Workflow", "triggerCategory": 2, "os": 1},
                {"buildProfileName": "Android Build", "branchName": "main", "buildStatus": 0,
                 "buildStartDate": "2026-01-05T10:00:00Z", "buildDuration": 3.0,
                 "workflowName": "Default Push Workflow", "triggerCategory": 2, "os": 2},
            ],
        }
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=two_profile_history))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=[
            {"id": "p1", "name": "iOS Build", "lastBuildDate": "2026-01-05T10:00:00Z"},
            {"id": "p2", "name": "Android Build", "lastBuildDate": "2026-01-05T10:00:00Z"},
        ]))
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=[{"id": "push-id", "workflowName": "Default Push Workflow"}])
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        mocked_api.get("/build/v2/profiles/p2/workflows/").mock(
            return_value=Response(200, json=[{"id": "push-id-2", "workflowName": "Default Push Workflow"}])
        )
        mocked_api.get("/build/v2/profiles/p2/workflows/push-id-2").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        # iOS Build: confirmed not configured. Android Build: fetch denied (unknown).
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(return_value=Response(200, json={
            "pullRequestSettings": [], "pushSettings": [{"workflowId": "push-id"}], "tagSettings": [],
        }))
        mocked_api.get("/build/v1/profiles/p2/triggers").mock(return_value=Response(403, json={"message": "Forbidden"}))
        _mock_empty_signing_identities(mocked_api)

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        assert "triggers:Android Build" in result["meta"]["failed_fetches"]
        top_improvements = result["data"]["sections"]["maturity_assessment"]["top_improvements"]
        pr_not_configured = [i for i in top_improvements if i["check"] == "pr_workflow_not_configured"]
        assert pr_not_configured == [{"check": "pr_workflow_not_configured", "severity": "advisory", "profiles": ["iOS Build"]}]

    async def test_certificates_401_omits_security_not_falsely_clean(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(200, json=SECURITY_BUILD_HISTORY_RESPONSE))
        mocked_api.get("/build/v2/profiles").mock(return_value=Response(200, json=WORKFLOW_QUALITY_PROFILES_RESPONSE))
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=WORKFLOW_QUALITY_WORKFLOW_LIST_RESPONSE)
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Default Push Workflow", "workflowDocument": WORKFLOW_QUALITY_PUSH_YAML})
        )
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={"pullRequestSettings": [], "pushSettings": [{"workflowId": "push-id"}], "tagSettings": []})
        )
        mocked_api.get("/build/v2/profiles/p1/configurations").mock(
            return_value=Response(200, json=[
                {"item1": {"id": "cfg-1", "configurationName": "Default Configuration"}, "item2": []},
            ])
        )
        mocked_api.get("/build/v2/profiles/p1/configurations/cfg-1").mock(
            return_value=Response(200, json={
                "environmentVariables": [],
                "signingIdentities": [{"signingIdentityType": 2, "entityId": "cert-1", "bundleIdentifier": None}],
            })
        )
        mocked_api.get("/signing-identity/v2/certificates").mock(return_value=Response(401, json={"message": "Unauthorized"}))
        mocked_api.get("/signing-identity/v2/provisioning-profiles").mock(return_value=Response(200, json=[]))
        mocked_api.get("/signing-identity/v2/keystores").mock(return_value=Response(200, json=[]))

        result = await get_build_insights_report(
            sections=["maturity_assessment"], start_date="2026-01-01", end_date="2026-01-10"
        )

        assert result["success"] is True
        maturity = result["data"]["sections"]["maturity_assessment"]
        # Couldn't verify certificates -> Security omitted entirely, not a
        # fabricated clean signing-health score from the unresolvable entityId.
        assert maturity["security"] is None
        assert "maturity_assessment.security" in result["meta"]["omitted_subsections"]
        assert "certificates" in result["meta"]["failed_fetches"]
        assert isinstance(maturity["overall_score"], int)

    async def test_current_period_failure_still_hard_fails_whole_call(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(500, json={"message": "Internal error"}))

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is False
        assert result["error"]["type"] == "http_error"


@pytest.mark.asyncio
class TestGetBuildInsightsReportValidation:
    async def test_invalid_section_returns_validation_error(self, mocked_api):
        result = await get_build_insights_report(sections=["nonexistent_section"])

        assert result["success"] is False
        assert result["error"]["tool"] == "get_build_insights_report"
        assert result["error"]["type"] == "validation_error"

    async def test_empty_sections_list_returns_validation_error(self, mocked_api):
        result = await get_build_insights_report(sections=[])

        assert result["success"] is False
        assert result["error"]["type"] == "validation_error"


@pytest.mark.asyncio
class TestGetBuildInsightsReportErrors:
    async def test_api_error_returns_standard_envelope(self, mocked_api):
        mocked_api.get("/report/v2/build").mock(return_value=Response(500, json={"message": "Internal error"}))

        result = await get_build_insights_report(start_date="2026-01-01", end_date="2026-01-10")

        assert result["success"] is False
        assert result["error"]["tool"] == "get_build_insights_report"
        assert result["error"]["type"] == "http_error"
