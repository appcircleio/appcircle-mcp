"""Unit tests for build-insights Root Cause compute functions. Pure-function
tests against fabricated build records -- no HTTP involved."""

from src.tools.report.build_insights.root_cause import (
    flaky_cards,
    mttr_cards,
    top_failing_steps,
    warning_hotspot_cards,
    zero_success_workflow_cards,
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


class TestTopFailingSteps:
    def test_returns_none_when_failed_step_absent(self):
        curr = [_build(status=1)]
        assert top_failing_steps(curr) is None

    def test_returns_empty_list_when_no_failures(self):
        curr = [_build(status=0, failedStep=None)]
        assert top_failing_steps(curr) == []

    def test_splits_comma_separated_steps_and_counts_each(self):
        curr = [_build(status=1, failedStep="Step A, Step B")]
        rows = top_failing_steps(curr)
        steps = {r["step"]: r["count"] for r in rows}
        assert steps == {"Step A": 1, "Step B": 1}

    def test_top_combos_per_step(self):
        curr = [
            _build(profile="A", branch="main", status=1, failedStep="Step A"),
            _build(profile="A", branch="main", status=1, failedStep="Step A"),
            _build(profile="B", branch="dev", status=1, failedStep="Step A"),
        ]
        rows = top_failing_steps(curr)
        assert rows[0]["count"] == 3
        assert rows[0]["top_combos"][0] == {"profile": "A", "branch": "main", "count": 2}

    def test_pct_of_failed_across_multiple_steps(self):
        curr = [
            _build(status=1, failedStep="Step A"),
            _build(status=1, failedStep="Step A"),
            _build(status=1, failedStep="Step A"),
            _build(status=1, failedStep="Step B"),
        ]
        rows = top_failing_steps(curr)
        by_step = {r["step"]: r["pct_of_failed"] for r in rows}
        assert by_step == {"Step A": 75.0, "Step B": 25.0}

    def test_ignores_failed_step_on_warned_but_successful_builds(self):
        """failedStep is also populated on warned (non-fatal) successes --
        those belong to warning_hotspot_cards, not this failures-only view."""
        curr = [_build(status=0, hasWarning=True, failedStep="Step A")]
        assert top_failing_steps(curr) == []

    def test_limit_caps_number_of_steps_returned(self):
        curr = [_build(status=1, failedStep=f"Step {i}") for i in range(10)]
        assert len(top_failing_steps(curr, limit=3)) == 3


class TestMttrCards:
    def test_delegates_to_shared_episode_computation(self):
        curr = [
            _build(status=1, start="2026-01-01T00:00:00Z"),
            _build(status=0, start="2026-01-01T02:00:00Z"),
        ]
        cards = mttr_cards(curr)
        assert cards[0]["avg_hours"] == 2.0

    def test_empty_list_when_no_episodes(self):
        assert mttr_cards([_build(status=0)]) == []


class TestFlakyCards:
    def test_returns_none_when_commit_id_absent(self):
        curr = [_build(status=1, workflowName="wf")]
        assert flaky_cards(curr) is None

    def test_returns_none_when_workflow_name_absent(self):
        curr = [_build(status=1, commitId="c1")]
        assert flaky_cards(curr) is None

    def test_detects_flaky_combo(self):
        curr = [
            _build(status=1, duration=1.0, workflowName="wf", commitId="c1"),
            _build(status=0, duration=2.0, workflowName="wf", commitId="c1"),
        ]
        cards = flaky_cards(curr)
        assert cards[0]["wasted_minutes"] == 3.0


class TestWarningHotspotCards:
    def test_returns_none_when_has_warning_absent(self):
        assert warning_hotspot_cards([_build(status=0)]) is None

    def test_ranks_combos_by_warned_count_with_top_step(self):
        curr = [
            _build(profile="A", branch="main", hasWarning=True, failedStep="Step A"),
            _build(profile="A", branch="main", hasWarning=True, failedStep="Step A"),
            _build(profile="B", branch="dev", hasWarning=False),
        ]
        cards = warning_hotspot_cards(curr)
        assert cards == [{"profile": "A", "branch": "main", "warned_count": 2, "top_warning_step": "Step A"}]

    def test_warned_build_with_no_failed_step_has_no_top_step(self):
        curr = [_build(profile="A", branch="main", hasWarning=True, failedStep=None)]
        cards = warning_hotspot_cards(curr)
        assert cards == [{"profile": "A", "branch": "main", "warned_count": 1, "top_warning_step": None}]


class TestZeroSuccessWorkflowCards:
    def test_returns_none_when_workflow_name_absent(self):
        assert zero_success_workflow_cards([_build(status=1)]) is None

    def test_requires_at_least_three_runs(self):
        curr = [_build(status=1, workflowName="wf") for _ in range(2)]
        assert zero_success_workflow_cards(curr) == []

    def test_excludes_combo_with_any_success(self):
        curr = [_build(status=1, workflowName="wf") for _ in range(2)] + [_build(status=0, workflowName="wf")]
        assert zero_success_workflow_cards(curr) == []

    def test_flags_combo_with_three_plus_runs_all_failed(self):
        curr = [_build(status=1, workflowName="wf", failedStep="Step A") for _ in range(3)]
        cards = zero_success_workflow_cards(curr)
        assert cards == [{"profile": "A", "workflow": "wf", "run_count": 3, "always_failing_step": "Step A"}]

    def test_builds_with_no_workflow_name_are_skipped(self):
        curr = [_build(status=1, workflowName=None) for _ in range(3)] + [
            _build(status=1, workflowName="wf", failedStep="Step A") for _ in range(3)
        ]
        cards = zero_success_workflow_cards(curr)
        assert cards == [{"profile": "A", "workflow": "wf", "run_count": 3, "always_failing_step": "Step A"}]
