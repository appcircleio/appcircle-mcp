"""Unit tests for build-insights shared algorithms: MTTR episodes, flaky
detection, percentile, and field_present. Pure-function tests against
fabricated build records -- no HTTP involved."""

from src.tools.report.build_insights.shared import (
    compute_flaky_groups,
    compute_mttr_episodes,
    field_present,
    parse_iso,
    percentile,
    top_flaky_combos,
    top_mttr_combos,
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


class TestParseIso:
    def test_parses_z_suffixed_timestamp(self):
        dt = parse_iso("2026-01-02T12:27:54Z")
        assert dt.year == 2026 and dt.month == 1 and dt.day == 2
        assert dt.hour == 12 and dt.minute == 27 and dt.second == 54


class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert percentile([], 50) == 0.0

    def test_single_value_returns_that_value(self):
        assert percentile([7.0], 95) == 7.0

    def test_p50_of_five_values(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3

    def test_p95_uses_linear_interpolation(self):
        assert abs(percentile([1, 2, 3, 4, 5], 95) - 4.8) < 1e-9

    def test_exact_index_boundary_returns_value_directly(self):
        assert percentile([1, 2, 3], 0) == 1
        assert percentile([1, 2, 3], 100) == 3


class TestFieldPresent:
    def test_true_when_at_least_one_build_has_value(self):
        builds = [_build(failedStep=None), _build(failedStep="Step A")]
        assert field_present(builds, "failedStep") is True

    def test_false_when_field_missing_or_empty_everywhere(self):
        builds = [_build(failedStep=None), _build(failedStep="")]
        assert field_present(builds, "failedStep") is False

    def test_false_when_field_entirely_absent(self):
        builds = [_build(), _build()]
        assert field_present(builds, "failedStep") is False


class TestComputeMttrEpisodes:
    def test_consecutive_failures_collapse_into_one_episode(self):
        builds = [
            _build(status=1, start="2026-01-01T00:00:00Z"),
            _build(status=1, start="2026-01-01T01:00:00Z"),
            _build(status=0, start="2026-01-01T03:00:00Z"),
        ]
        episodes = compute_mttr_episodes(builds)
        assert len(episodes) == 1
        assert episodes[0]["duration_hours"] == 3.0

    def test_open_episode_at_period_end_is_excluded(self):
        builds = [
            _build(status=0, start="2026-01-01T00:00:00Z"),
            _build(status=1, start="2026-01-01T01:00:00Z"),
        ]
        assert compute_mttr_episodes(builds) == []

    def test_canceled_and_unknown_status_are_transparent(self):
        builds = [
            _build(status=1, start="2026-01-01T00:00:00Z"),
            _build(status=2, start="2026-01-01T00:30:00Z"),
            _build(status=99, start="2026-01-01T00:45:00Z"),
            _build(status=0, start="2026-01-01T02:00:00Z"),
        ]
        episodes = compute_mttr_episodes(builds)
        assert len(episodes) == 1
        assert episodes[0]["duration_hours"] == 2.0

    def test_separate_branches_tracked_independently(self):
        builds = [
            _build(branch="main", status=1, start="2026-01-01T00:00:00Z"),
            _build(branch="main", status=0, start="2026-01-01T01:00:00Z"),
            _build(branch="dev", status=1, start="2026-01-01T00:00:00Z"),
            _build(branch="dev", status=0, start="2026-01-01T05:00:00Z"),
        ]
        episodes = compute_mttr_episodes(builds)
        by_branch = {e["branch"]: e["duration_hours"] for e in episodes}
        assert by_branch == {"main": 1.0, "dev": 5.0}

    def test_a_success_with_no_prior_failure_is_a_no_op(self):
        builds = [_build(status=0, start="2026-01-01T00:00:00Z")]
        assert compute_mttr_episodes(builds) == []


class TestTopMttrCombos:
    def test_ranks_longest_avg_mttr_first(self):
        episodes = [
            {"profile": "A", "branch": "main", "duration_hours": 1.0},
            {"profile": "B", "branch": "main", "duration_hours": 5.0},
            {"profile": "C", "branch": "main", "duration_hours": 2.0},
        ]
        top = top_mttr_combos(episodes, limit=2)
        assert [r["profile"] for r in top] == ["B", "C"]

    def test_averages_multiple_episodes_for_same_combo(self):
        episodes = [
            {"profile": "A", "branch": "main", "duration_hours": 2.0},
            {"profile": "A", "branch": "main", "duration_hours": 4.0},
        ]
        top = top_mttr_combos(episodes)
        assert top[0]["avg_hours"] == 3.0
        assert top[0]["sequence_count"] == 2


class TestComputeFlakyGroups:
    def test_same_commit_success_and_failure_is_flaky(self):
        builds = [
            _build(status=1, duration=1.0, workflowName="wf", commitId="c1"),
            _build(status=0, duration=2.0, workflowName="wf", commitId="c1"),
        ]
        flaky = compute_flaky_groups(builds)
        assert len(flaky) == 1
        assert flaky[0]["wasted_minutes"] == 3.0
        assert flaky[0]["build_count"] == 2

    def test_all_success_same_commit_is_not_flaky(self):
        builds = [
            _build(status=0, workflowName="wf", commitId="c1"),
            _build(status=0, workflowName="wf", commitId="c1"),
        ]
        assert compute_flaky_groups(builds) == []

    def test_canceled_builds_in_flaky_group_count_toward_wasted_time(self):
        builds = [
            _build(status=1, duration=1.0, workflowName="wf", commitId="c1"),
            _build(status=0, duration=2.0, workflowName="wf", commitId="c1"),
            _build(status=2, duration=0.5, workflowName="wf", commitId="c1"),
        ]
        flaky = compute_flaky_groups(builds)
        assert flaky[0]["wasted_minutes"] == 3.5
        assert flaky[0]["build_count"] == 3

    def test_missing_workflow_or_commit_id_is_skipped(self):
        builds = [
            _build(status=1, workflowName=None, commitId="c1"),
            _build(status=0, workflowName="wf", commitId=None),
        ]
        assert compute_flaky_groups(builds) == []


class TestTopFlakyCombos:
    def test_ranks_by_wasted_time_aggregating_across_workflows(self):
        flaky_groups = [
            {"profile": "A", "branch": "main", "workflow": "wf1", "commit_id": "c1", "wasted_minutes": 3.0},
            {"profile": "A", "branch": "main", "workflow": "wf2", "commit_id": "c2", "wasted_minutes": 4.0},
            {"profile": "B", "branch": "main", "workflow": "wf1", "commit_id": "c3", "wasted_minutes": 1.0},
        ]
        top = top_flaky_combos(flaky_groups)
        assert top[0]["profile"] == "A"
        assert top[0]["flaky_commit_count"] == 2
        assert top[0]["wasted_minutes"] == 7.0
