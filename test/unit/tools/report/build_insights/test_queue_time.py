"""Unit tests for build-insights Queue Time compute functions. Pure-function
tests against fabricated /report/v1/build/queue-waiting records -- no HTTP
involved. Note: `buildDuration` here means queue wait minutes, not
execution time like on /report/v2/build."""

from src.tools.report.build_insights.queue_time import (
    compute_queue_wait_summary,
    daily_queue_wait_trend,
    plan_wait_breakdown,
)


def _build(status=0, start="2026-01-01T00:00:00Z", wait=1.0):
    return {"buildStatus": status, "buildStartDate": start, "buildDuration": wait}


class TestComputeQueueWaitSummary:
    def test_matches_real_example_totals(self):
        # 4 records, each wait=1.0, total=4.0
        builds = [_build(status=0, wait=1.0), _build(status=2, wait=1.0), _build(status=2, wait=1.0), _build(status=0, wait=1.0)]
        summary = compute_queue_wait_summary(builds)
        assert summary["total_wait_minutes"] == 4.0
        assert summary["avg_wait_minutes"] == 1.0
        assert summary["build_count"] == 4

    def test_percentiles_computed_correctly(self):
        builds = [_build(wait=w) for w in [1, 2, 3, 4, 5]]
        summary = compute_queue_wait_summary(builds)
        assert summary["p50_wait_minutes"] == 3
        assert abs(summary["p95_wait_minutes"] - 4.8) < 1e-9

    def test_returns_none_for_empty_input(self):
        assert compute_queue_wait_summary([]) is None

    def test_returns_none_when_only_in_progress_builds(self):
        builds = [_build(status=90), _build(status=91), _build(status=92)]
        assert compute_queue_wait_summary(builds) is None

    def test_canceled_and_failed_builds_are_included(self):
        builds = [_build(status=2, wait=5.0), _build(status=1, wait=3.0)]
        summary = compute_queue_wait_summary(builds)
        assert summary["build_count"] == 2
        assert summary["total_wait_minutes"] == 8.0

    def test_in_progress_builds_excluded_from_otherwise_valid_set(self):
        builds = [_build(status=0, wait=2.0), _build(status=90, wait=999.0)]
        summary = compute_queue_wait_summary(builds)
        assert summary["build_count"] == 1
        assert summary["total_wait_minutes"] == 2.0


class TestPlanWaitBreakdown:
    def test_matches_real_example_totals(self):
        # 0 standard, all 4 minutes on velocity, 0 ultra.
        summary = {"totalBuildsRun": 4, "totalBuildWaitingDuration": 4.0, "standard": 0.0, "velocity": 4.0, "ultra": 0.0}
        assert plan_wait_breakdown(summary) == {
            "standard_wait_minutes": 0.0,
            "velocity_wait_minutes": 4.0,
            "ultra_wait_minutes": 0.0,
        }

    def test_returns_none_for_none_summary(self):
        assert plan_wait_breakdown(None) is None

    def test_returns_none_for_empty_summary(self):
        assert plan_wait_breakdown({}) is None

    def test_returns_none_when_no_plan_fields_present(self):
        # e.g. an older/stripped response with only the aggregate totals.
        summary = {"totalBuildsRun": 2, "totalBuildWaitingDuration": 3.0}
        assert plan_wait_breakdown(summary) is None

    def test_missing_individual_plan_field_defaults_to_zero(self):
        summary = {"standard": 2.0, "velocity": 1.0}  # no "ultra" key at all
        assert plan_wait_breakdown(summary) == {
            "standard_wait_minutes": 2.0,
            "velocity_wait_minutes": 1.0,
            "ultra_wait_minutes": 0.0,
        }


class TestDailyQueueWaitTrend:
    def test_groups_by_calendar_day_of_build_start_date(self):
        builds = [
            _build(start="2026-01-01T08:00:00Z", wait=2.0),
            _build(start="2026-01-01T09:00:00Z", wait=4.0),
            _build(start="2026-01-03T08:00:00Z", wait=1.0),
        ]
        trend = daily_queue_wait_trend(builds)
        assert trend == [
            {"date": "2026-01-01", "avg_wait_minutes": 3.0},
            {"date": "2026-01-03", "avg_wait_minutes": 1.0},
        ]

    def test_days_with_no_valid_builds_are_absent_not_zero(self):
        builds = [_build(start="2026-01-01T00:00:00Z"), _build(start="2026-01-05T00:00:00Z")]
        trend = daily_queue_wait_trend(builds)
        dates = [pt["date"] for pt in trend]
        assert dates == ["2026-01-01", "2026-01-05"]  # no entries for 01-02..01-04

    def test_empty_input_returns_empty_list(self):
        assert daily_queue_wait_trend([]) == []

    def test_in_progress_builds_excluded(self):
        builds = [_build(status=90, start="2026-01-01T00:00:00Z")]
        assert daily_queue_wait_trend(builds) == []
