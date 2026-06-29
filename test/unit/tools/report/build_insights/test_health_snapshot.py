"""Unit tests for build-insights Health Snapshot + Trends compute functions.
Pure-function tests against fabricated build records -- no HTTP involved."""

from datetime import date

from src.tools.report.build_insights.health_snapshot import (
    compute_summary,
    daily_series,
    inactive_profiles,
    per_profile_duration,
    per_profile_duration_series,
    top_active_profiles,
    top_build_activity,
    top_triggers,
)


def _build(profile="A", branch="main", status=0, start="2026-01-01T00:00:00Z", duration=1.0, **extra):
    return {
        "buildProfileName": profile,
        "branchName": branch,
        "buildStatus": status,
        "buildStartDate": start,
        "buildDuration": duration,
        **extra,
    }


class TestComputeSummary:
    def test_counts_and_rates_for_current_period(self):
        curr = [_build(status=0), _build(status=0), _build(status=1), _build(status=2)]
        summary = compute_summary(curr, [])
        assert summary["current"]["total"] == 4
        assert summary["current"]["success"] == 2
        assert summary["current"]["failed"] == 1
        assert summary["current"]["canceled"] == 1
        assert summary["current"]["success_rate"] == 50.0

    def test_delta_rate_is_percentage_points_not_percent_of_percent(self):
        curr = [_build(status=0), _build(status=1)]  # 50% success
        prev = [_build(status=0), _build(status=0), _build(status=0), _build(status=1)]  # 75% success
        summary = compute_summary(curr, prev)
        assert summary["delta"]["success_rate_pp"] == -25.0

    def test_delta_is_none_with_no_previous_baseline(self):
        summary = compute_summary([_build(status=0)], [])
        assert summary["delta"]["total_pct"] is None
        assert summary["delta"]["success_rate_pp"] is None
        assert summary["delta"]["failure_rate_pp"] is None
        assert summary["delta"]["canceled_rate_pp"] is None

    def test_failure_and_canceled_rate_deltas_are_percentage_points(self):
        curr = [_build(status=1), _build(status=1), _build(status=2)]  # 67% failed, 33% canceled
        prev = [_build(status=1), _build(status=0), _build(status=0), _build(status=0)]  # 25% failed, 0% canceled
        summary = compute_summary(curr, prev)
        assert round(summary["delta"]["failure_rate_pp"], 2) == 41.67
        assert round(summary["delta"]["canceled_rate_pp"], 2) == 33.33

    def test_count_volume_change_does_not_skew_rate_deltas(self):
        """Doubling build volume with the same failure rate should show a 0pp
        rate delta, even though the raw failed count also doubled."""
        curr = [_build(status=0)] * 6 + [_build(status=1)] * 2  # 8 builds, 25% failed
        prev = [_build(status=0)] * 3 + [_build(status=1)] * 1  # 4 builds, 25% failed
        summary = compute_summary(curr, prev)
        assert summary["delta"]["total_pct"] == 100.0
        assert summary["delta"]["failure_rate_pp"] == 0.0

    def test_empty_period_has_zero_rates_not_division_error(self):
        summary = compute_summary([], [])
        assert summary["current"]["success_rate"] == 0.0


class TestTopActiveProfiles:
    def test_ranks_by_build_count_descending(self):
        curr = [_build(profile="A")] * 3 + [_build(profile="B")] * 5
        top = top_active_profiles(curr)
        assert [r["profile"] for r in top] == ["B", "A"]

    def test_success_rate_per_profile(self):
        curr = [_build(profile="A", status=0), _build(profile="A", status=1)]
        top = top_active_profiles(curr)
        assert top[0]["success_rate"] == 50.0

    def test_limit_caps_results(self):
        curr = [_build(profile=f"P{i}") for i in range(10)]
        assert len(top_active_profiles(curr, limit=3)) == 3


class TestInactiveProfiles:
    def test_profile_with_no_last_build_date_is_inactive(self):
        profiles = [{"name": "X", "lastBuildDate": None}]
        result = inactive_profiles(profiles, date(2026, 1, 15))
        assert result == [{"profile": "X", "last_build_date": None}]

    def test_profile_with_old_last_build_date_is_inactive(self):
        profiles = [{"name": "X", "lastBuildDate": "2025-11-01T00:00:00Z"}]
        result = inactive_profiles(profiles, date(2026, 1, 15))
        assert len(result) == 1

    def test_profile_with_recent_last_build_date_is_active(self):
        profiles = [{"name": "X", "lastBuildDate": "2026-01-10T00:00:00Z"}]
        assert inactive_profiles(profiles, date(2026, 1, 15)) == []

    def test_exactly_30_days_is_still_active(self):
        profiles = [{"name": "X", "lastBuildDate": "2025-12-16T00:00:00Z"}]
        assert inactive_profiles(profiles, date(2026, 1, 15)) == []


class TestTopBuildActivity:
    def test_groups_by_profile_and_branch(self):
        curr = [_build(profile="A", branch="main")] * 2 + [_build(profile="A", branch="dev")]
        rows = top_build_activity(curr)
        by_branch = {r["branch"]: r["build_count"] for r in rows}
        assert by_branch == {"main": 2, "dev": 1}


class TestTopTriggers:
    def test_returns_none_when_fields_absent(self):
        curr = [_build()]
        assert top_triggers(curr) is None

    def test_splits_manual_and_automated_by_trigger_category(self):
        curr = [
            _build(triggerCategory=0, initiatedBy="dev@example.com"),
            _build(triggerCategory=1, initiatedBy="ci-bot"),
        ]
        result = top_triggers(curr)
        assert result["manual"] == [{"initiated_by": "dev@example.com", "build_count": 1}]
        assert result["automated"] == [{"initiated_by": "ci-bot", "build_count": 1}]

    def test_excludes_null_and_placeholder_initiators(self):
        curr = [
            _build(triggerCategory=0, initiatedBy=None),
            _build(triggerCategory=0, initiatedBy="N/A"),
            _build(triggerCategory=0, initiatedBy="00000000-0000-0000-0000-000000000000"),
        ]
        result = top_triggers(curr)
        assert result["manual"] == []


class TestDailySeries:
    def test_fills_gaps_with_zero(self):
        curr = [_build(start="2026-01-01T00:00:00Z", status=0)]
        series = daily_series(curr, date(2026, 1, 1), date(2026, 1, 3))
        assert [d["date"] for d in series] == ["2026-01-01", "2026-01-02", "2026-01-03"]
        assert series[1]["total"] == 0
        assert series[0]["total"] == 1

    def test_timeout_counts_toward_both_failed_and_timeout(self):
        curr = [_build(start="2026-01-01T00:00:00Z", status=3)]
        series = daily_series(curr, date(2026, 1, 1), date(2026, 1, 1))
        assert series[0]["failed"] == 1
        assert series[0]["timeout"] == 1

    def test_canceled_status_counts_toward_canceled_bucket(self):
        curr = [_build(start="2026-01-01T00:00:00Z", status=2)]
        series = daily_series(curr, date(2026, 1, 1), date(2026, 1, 1))
        assert series[0]["canceled"] == 1


class TestPerProfileDuration:
    def test_p50_p95_and_consistency(self):
        curr = [_build(profile="A", status=0, duration=d) for d in [3, 3, 3, 3, 4]]
        rows = per_profile_duration(curr, [], ["A"])
        assert rows[0]["p50"] == 3
        assert rows[0]["consistency"] == "consistent"

    def test_high_p95_p50_ratio_is_moderate_or_high_variance(self):
        curr = [_build(profile="A", status=0, duration=d) for d in [1, 2, 3, 4, 5]]
        rows = per_profile_duration(curr, [], ["A"])
        assert abs(rows[0]["ratio"] - 1.6) < 1e-9
        assert rows[0]["consistency"] == "moderate"

    def test_skips_profile_with_no_successful_builds(self):
        curr = [_build(profile="A", status=1)]
        assert per_profile_duration(curr, [], ["A"]) == []

    def test_trend_compares_to_previous_period_p50(self):
        curr = [_build(profile="A", status=0, duration=10)]
        prev = [_build(profile="A", status=0, duration=5)]
        rows = per_profile_duration(curr, prev, ["A"])
        assert rows[0]["trend"] == "slower"

    def test_trend_faster_when_p50_drops_more_than_10_percent(self):
        curr = [_build(profile="A", status=0, duration=5)]
        prev = [_build(profile="A", status=0, duration=10)]
        rows = per_profile_duration(curr, prev, ["A"])
        assert rows[0]["trend"] == "faster"

    def test_high_variance_when_ratio_exceeds_2(self):
        curr = [_build(profile="A", status=0, duration=d) for d in [1, 1, 1, 1, 100]]
        rows = per_profile_duration(curr, [], ["A"])
        assert rows[0]["consistency"] == "high variance"


class TestPerProfileDurationSeries:
    def test_p50_for_a_day_with_at_least_two_successful_builds(self):
        curr = [
            _build(profile="A", status=0, start="2026-01-01T08:00:00Z", duration=4.0),
            _build(profile="A", status=0, start="2026-01-01T09:00:00Z", duration=6.0),
        ]
        rows = per_profile_duration_series(curr, date(2026, 1, 1), date(2026, 1, 1), ["A"])
        assert rows == [{"profile": "A", "series": [{"date": "2026-01-01", "p50": 5.0}]}]

    def test_day_with_fewer_than_two_successful_builds_is_null_not_zero(self):
        curr = [_build(profile="A", status=0, start="2026-01-01T08:00:00Z", duration=4.0)]
        rows = per_profile_duration_series(curr, date(2026, 1, 1), date(2026, 1, 1), ["A"])
        assert rows[0]["series"][0]["p50"] is None

    def test_failed_builds_do_not_count_toward_the_two_build_minimum(self):
        curr = [
            _build(profile="A", status=0, start="2026-01-01T08:00:00Z", duration=4.0),
            _build(profile="A", status=1, start="2026-01-01T09:00:00Z", duration=6.0),
        ]
        rows = per_profile_duration_series(curr, date(2026, 1, 1), date(2026, 1, 1), ["A"])
        assert rows[0]["series"][0]["p50"] is None

    def test_every_day_in_range_appears_even_with_no_builds(self):
        rows = per_profile_duration_series([], date(2026, 1, 1), date(2026, 1, 3), ["A"])
        assert [pt["date"] for pt in rows[0]["series"]] == ["2026-01-01", "2026-01-02", "2026-01-03"]
        assert all(pt["p50"] is None for pt in rows[0]["series"])

    def test_one_series_per_top_profile_independently(self):
        curr = [
            _build(profile="A", status=0, start="2026-01-01T08:00:00Z", duration=4.0),
            _build(profile="A", status=0, start="2026-01-01T09:00:00Z", duration=6.0),
            _build(profile="B", status=0, start="2026-01-01T08:00:00Z", duration=100.0),
        ]
        rows = per_profile_duration_series(curr, date(2026, 1, 1), date(2026, 1, 1), ["A", "B"])
        by_profile = {r["profile"]: r["series"][0]["p50"] for r in rows}
        assert by_profile == {"A": 5.0, "B": None}

    def test_builds_from_profiles_outside_top_profiles_are_ignored(self):
        curr = [
            _build(profile="C", status=0, start="2026-01-01T08:00:00Z", duration=1.0),
            _build(profile="C", status=0, start="2026-01-01T09:00:00Z", duration=2.0),
        ]
        rows = per_profile_duration_series(curr, date(2026, 1, 1), date(2026, 1, 1), ["A"])
        assert rows == [{"profile": "A", "series": [{"date": "2026-01-01", "p50": None}]}]
