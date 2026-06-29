"""Unit tests for build-insights Maturity Assessment compute functions.
Pure-function tests against fabricated build records / pre-computed section
data -- no HTTP involved."""

from datetime import datetime, timezone

from src.tools.report.build_insights.maturity_assessment import (
    combine_overall_score,
    discipline_score,
    flaky_factor,
    mttr_factor,
    reliability_score,
    security_score,
    speed_score,
    success_rate_factor,
    top_improvements,
    warning_hotspot_factor,
)


def _build(profile="A", branch="main", status=0, start="2026-01-01T00:00:00Z", workflow="WF", commit="c1", os_=1, has_warning=False, duration=10.0):
    return {
        "buildProfileName": profile,
        "branchName": branch,
        "buildStatus": status,
        "buildStartDate": start,
        "workflowName": workflow,
        "commitId": commit,
        "os": os_,
        "hasWarning": has_warning,
        "buildDuration": duration,
    }


class TestSuccessRateFactor:
    def test_boundary_values_map_to_breakpoint_table(self):
        cases = [
            (1.0, 100), (0.95, 100), (0.94, 90), (0.90, 90), (0.89, 80),
            (0.85, 80), (0.80, 70), (0.75, 60), (0.70, 50), (0.60, 40), (0.10, 20),
        ]
        for rate, expected_score in cases:
            success = round(rate * 100)
            builds = [_build(status=0)] * success + [_build(status=1)] * (100 - success)
            assert success_rate_factor(builds)["factor_score"] == expected_score, rate

    def test_empty_input_is_zero_rate(self):
        result = success_rate_factor([])
        assert result == {"value": 0.0, "factor_score": 20}


class TestMttrFactor:
    def test_boundary_values_map_to_breakpoint_table(self):
        def episode_builds(hours):
            return [
                _build(status=1, start="2026-01-01T00:00:00Z"),
                _build(status=0, start=f"2026-01-01T{hours:02d}:00:00Z"),
            ]

        cases = [(1, 100), (2, 90), (3, 80), (4, 70), (6, 60), (8, 50), (12, 40), (13, 20)]
        for hours, expected_score in cases:
            assert mttr_factor(episode_builds(hours))["factor_score"] == expected_score, hours

    def test_no_episodes_is_perfect_score(self):
        result = mttr_factor([_build(status=0)])
        assert result == {"value_hours": 0.0, "factor_score": 100}


class TestFlakyFactor:
    def test_rate_boundaries(self):
        # 5 top profiles; vary how many are flaky.
        top_profiles = ["A", "B", "C", "D", "E"]

        def flaky_builds(flaky_count):
            builds = []
            for i, profile in enumerate(top_profiles):
                if i < flaky_count:
                    builds.append(_build(profile=profile, status=0, commit="shared"))
                    builds.append(_build(profile=profile, status=1, commit="shared"))
            return builds

        cases = [(0, 100), (1, 80), (2, 60), (3, 40), (4, 20), (5, 20)]
        for count, expected_score in cases:
            result = flaky_factor(flaky_builds(count), top_profiles)
            assert result["count"] == count
            assert result["factor_score"] == expected_score, count

    def test_empty_top_profiles_does_not_crash(self):
        assert flaky_factor([], []) == {"count": 0, "factor_score": 100}


class TestWarningHotspotFactor:
    def test_none_when_has_warning_field_entirely_missing(self):
        builds = [{"buildProfileName": "A", "buildStatus": 0}]
        assert warning_hotspot_factor(builds, ["A"]) is None

    def test_hotspot_when_warned_share_meets_threshold(self):
        builds = (
            [_build(profile="A", status=0, has_warning=True)] * 3
            + [_build(profile="A", status=0, has_warning=False)] * 7
        )
        result = warning_hotspot_factor(builds, ["A", "B", "C", "D", "E"])
        assert result == {"count": 1, "factor_score": 80}

    def test_not_a_hotspot_below_threshold(self):
        builds = (
            [_build(profile="A", status=0, has_warning=True)] * 2
            + [_build(profile="A", status=0, has_warning=False)] * 8
        )
        result = warning_hotspot_factor(builds, ["A"])
        assert result == {"count": 0, "factor_score": 100}

    def test_profile_with_no_successful_builds_is_not_counted(self):
        builds = [_build(profile="A", status=1, has_warning=True)]
        result = warning_hotspot_factor(builds, ["A"])
        assert result == {"count": 0, "factor_score": 100}


class TestReliabilityScore:
    def test_combines_four_factors_with_their_weights(self):
        builds = [_build(profile="A", status=0, has_warning=False)] * 10
        result = reliability_score(builds, ["A"])
        # success_rate=1.0->100, mttr no episodes->100, flaky 0->100, warning 0->100
        assert result["score"] == 100

    def test_renormalizes_weights_when_warning_hotspots_unavailable(self):
        builds = [{"buildProfileName": "A", "buildStatus": 0, "buildStartDate": "2026-01-01T00:00:00Z",
                   "branchName": "main", "workflowName": "WF", "commitId": "c1"}] * 10
        result = reliability_score(builds, ["A"])
        assert result["factors"]["warning_hotspots"] is None
        # All other factors are perfect (success_rate=100, mttr=100, flaky=100) -> renormalized still 100
        assert result["score"] == 100


class TestDisciplineScore:
    def test_combines_workflow_completeness_and_best_practice_checks(self):
        per_profile_quality = [
            {"profile": "A", "os": 1, "push": {"workflow_name": "Push", "total_score": 80}, "pr": None},
            {"profile": "B", "os": 2, "push": {"workflow_name": "Push", "total_score": 60}, "pr": {"workflow_name": "PR", "total_score": 90}},
        ]
        issues = [
            {"check": "versioning_not_automated", "severity": "critical", "profile": "B", "workflow": "Push"},
            {"check": "custom_script_not_from_git", "severity": "advisory", "profile": "A", "workflow": "Push", "count": 1},
        ]
        pr_configured = {"A": True, "B": False}
        result = discipline_score(per_profile_quality, issues, pr_configured, ["A", "B"])
        # wf_completeness = mean(80, 60, 90) = 76.67 -> 77
        # versioning: applicable=2, failing={B} -> passing=1 -> 1/2*33.33=16.67
        # git_scripts: passing = 2 - 1(A) = 1 -> 1/2*33.33=16.67
        # pr_configured: passing = 1(A) -> 1/2*33.33=16.67 -> bp_score=50.0
        # discipline = round(76.67*.5 + 50*.5) = round(63.33) = 63
        assert result == {"score": 63, "wf_completeness_score": 77, "bp_score": 50}

    def test_none_when_no_workflow_yaml_resolved_at_all(self):
        per_profile_quality = [{"profile": "A", "os": 1, "push": None, "pr": None}]
        assert discipline_score(per_profile_quality, [], {}, ["A"]) is None

    def test_bp_score_capped_at_100(self):
        per_profile_quality = [{"profile": "A", "os": 1, "push": {"workflow_name": "Push", "total_score": 100}, "pr": None}]
        result = discipline_score(per_profile_quality, [], {"A": True}, ["A"])
        assert result["bp_score"] == 100

    def test_pr_configured_none_excluded_from_applicable_population(self):
        # B's triggers fetch failed (unknown) -- must not be scored as "not
        # configured"; A alone (confirmed True) determines the check's result.
        per_profile_quality = [
            {"profile": "A", "os": 1, "push": {"workflow_name": "Push", "total_score": 100}, "pr": None},
            {"profile": "B", "os": 2, "push": {"workflow_name": "Push", "total_score": 100}, "pr": None},
        ]
        pr_configured = {"A": True, "B": None}
        result = discipline_score(per_profile_quality, [], pr_configured, ["A", "B"])
        assert result == {"score": 100, "wf_completeness_score": 100, "bp_score": 100}

    def test_pr_check_contributes_zero_when_all_profiles_unknown(self):
        per_profile_quality = [{"profile": "A", "os": 1, "push": {"workflow_name": "Push", "total_score": 100}, "pr": None}]
        result = discipline_score(per_profile_quality, [], {"A": None}, ["A"])
        # versioning 33.33 + git_scripts 33.33 + pr_configured 0 (no applicable profiles) -> bp_score=67
        assert result == {"score": 83, "wf_completeness_score": 100, "bp_score": 67}

    def test_versioning_not_applicable_contributes_zero_not_a_crash(self):
        # No profile has a resolved push workflow -- only a PR workflow.
        per_profile_quality = [{"profile": "A", "os": 1, "push": None, "pr": {"workflow_name": "PR", "total_score": 100}}]
        result = discipline_score(per_profile_quality, [], {"A": True}, ["A"])
        assert result is not None  # wf_completeness still computable from the PR score


class TestSpeedScore:
    def test_score_is_build_count_weighted_share_under_ratio_threshold(self):
        duration_rows = [
            {"profile": "A", "p50": 10, "ratio": 1.2},
            {"profile": "B", "p50": 10, "ratio": 3.0},
        ]
        top_profile_rows = [
            {"profile": "A", "build_count": 8},
            {"profile": "B", "build_count": 2},
        ]
        # weighted_avg_ratio = (1.2*8 + 3.0*2) / 10 = 1.56 -> "moderate" band
        assert speed_score(duration_rows, top_profile_rows) == {
            "score": 80, "weighted_avg_ratio": 1.56, "consistency": "moderate",
        }

    def test_ratio_exactly_at_threshold_is_not_consistent(self):
        duration_rows = [{"profile": "A", "p50": 10, "ratio": 1.5}]
        top_profile_rows = [{"profile": "A", "build_count": 5}]
        assert speed_score(duration_rows, top_profile_rows) == {
            "score": 0, "weighted_avg_ratio": 1.5, "consistency": "moderate",
        }

    def test_weighted_avg_ratio_consistency_bands(self):
        cases = [(1.0, "consistent"), (1.49, "consistent"), (1.5, "moderate"), (2.0, "moderate"), (2.1, "high variance")]
        for ratio, expected_band in cases:
            duration_rows = [{"profile": "A", "p50": 10, "ratio": ratio}]
            top_profile_rows = [{"profile": "A", "build_count": 5}]
            assert speed_score(duration_rows, top_profile_rows)["consistency"] == expected_band, ratio

    def test_none_when_no_duration_rows(self):
        assert speed_score([], []) is None

    def test_none_when_duration_row_profiles_have_no_build_count(self):
        duration_rows = [{"profile": "Z", "p50": 10, "ratio": 1.0}]
        top_profile_rows = [{"profile": "A", "build_count": 5}]
        assert speed_score(duration_rows, top_profile_rows) is None


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _config(env_vars=None, signing_identities=None):
    return {"environment_variables": env_vars or [], "signing_identities": signing_identities or []}


def _identity(entity_id):
    return {"signingIdentityType": 2, "entityId": entity_id, "bundleIdentifier": None}


class TestSecurityScore:
    def test_none_when_no_profile_resolves_a_configuration(self):
        result = security_score({"A": None}, ["A"], [], [], [], NOW)
        assert result is None

    def test_none_when_certificates_fetch_failed(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        result = security_score(configs, ["A"], None, [], [], NOW)
        assert result is None

    def test_none_when_provisioning_profiles_fetch_failed(self):
        configs = {"A": _config(signing_identities=[_identity("pp-1")])}
        result = security_score(configs, ["A"], [], None, [], NOW)
        assert result is None

    def test_none_when_keystores_fetch_failed(self):
        configs = {"A": _config(signing_identities=[_identity("ks-1")])}
        result = security_score(configs, ["A"], [], [], None, NOW)
        assert result is None

    def test_zero_signing_identities_is_full_signing_health_not_missing_data(self):
        configs = {"A": _config()}
        result = security_score(configs, ["A"], [], [], [], NOW)
        assert result["signing_health_score"] == 100
        assert result["expiring_soon"] == []

    def test_env_var_usage_score_from_presence_of_environment_variables(self):
        configs = {"A": _config(env_vars=["uuid-1"]), "B": _config(env_vars=[])}
        result = security_score(configs, ["A", "B"], [], [], [], NOW)
        assert result["env_var_usage_score"] == 50
        assert result["profiles_without_env_vars"] == ["B"]

    def test_unresolved_profiles_excluded_from_denominators(self):
        configs = {"A": _config(env_vars=["uuid-1"]), "B": None}
        result = security_score(configs, ["A", "B"], [], [], [], NOW)
        assert result["env_var_usage_score"] == 100  # only A counted, B unresolved

    def test_resolves_entity_by_membership_across_all_three_lists(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1"), _identity("pp-1"), _identity("ks-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2027-01-01T00:00:00+00:00"}]
        provisioning_profiles = [{"id": "pp-1", "name": "PP", "expireDate": "2027-01-01T00:00:00+00:00"}]
        keystores = [{"id": "ks-1", "name": "KS", "expireDate": "2027-01-01T00:00:00+00:00"}]
        result = security_score(configs, ["A"], certificates, provisioning_profiles, keystores, NOW)
        assert result["signing_health_score"] == 100  # all 3 resolved, none expiring

    def test_unresolvable_entity_id_is_skipped_not_a_crash(self):
        configs = {"A": _config(signing_identities=[_identity("does-not-exist")])}
        result = security_score(configs, ["A"], [], [], [], NOW)
        assert result["signing_health_score"] == 100  # not counted as a resolved identity at all
        assert result["expiring_soon"] == []

    def test_identity_with_missing_expire_date_is_skipped(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert"}]  # no expireDate
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert result["signing_health_score"] == 100
        assert result["expiring_soon"] == []

    def test_identity_with_unparseable_expire_date_is_skipped(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "not-a-date"}]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert result["signing_health_score"] == 100
        assert result["expiring_soon"] == []

    def test_signing_identity_entry_missing_entity_id_is_skipped(self):
        configs = {"A": _config(signing_identities=[{"signingIdentityType": 2, "entityId": None, "bundleIdentifier": None}])}
        result = security_score(configs, ["A"], [], [], [], NOW)
        assert result["signing_health_score"] == 100
        assert result["expiring_soon"] == []

    def test_expiring_within_30_days_flagged_critical_in_expiring_soon(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2026-01-15T00:00:00+00:00"}]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert result["signing_health_score"] == 0  # the only resolved identity is expiring
        assert result["expiring_soon"] == [
            {"type": "certificate", "id": "cert-1", "name": "Cert", "expire_date": "2026-01-15T00:00:00+00:00",
             "days_until_expiry": 14, "profiles": ["A"]}
        ]

    def test_already_expired_included_with_negative_days(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2025-12-01T00:00:00+00:00"}]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert result["expiring_soon"][0]["days_until_expiry"] == -31

    def test_not_expiring_beyond_30_days_excluded_from_expiring_soon(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2026-06-01T00:00:00+00:00"}]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert result["expiring_soon"] == []
        assert result["signing_health_score"] == 100

    def test_identity_shared_by_two_profiles_counted_once_with_both_profiles_listed(self):
        configs = {
            "A": _config(signing_identities=[_identity("cert-1")]),
            "B": _config(signing_identities=[_identity("cert-1")]),
        }
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2026-01-10T00:00:00+00:00"}]
        result = security_score(configs, ["A", "B"], certificates, [], [], NOW)
        assert len(result["expiring_soon"]) == 1
        assert result["expiring_soon"][0]["profiles"] == ["A", "B"]
        assert result["signing_health_score"] == 0  # 1 distinct identity, expiring -> 0%

    def test_expiring_soon_sorted_by_days_until_expiry_ascending(self):
        configs = {"A": _config(signing_identities=[_identity("cert-1"), _identity("cert-2")])}
        certificates = [
            {"id": "cert-1", "name": "Soon", "expireDate": "2026-01-20T00:00:00+00:00"},
            {"id": "cert-2", "name": "Sooner", "expireDate": "2026-01-05T00:00:00+00:00"},
        ]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        assert [item["name"] for item in result["expiring_soon"]] == ["Sooner", "Soon"]

    def test_overall_score_is_weighted_70_30(self):
        configs = {"A": _config(env_vars=[], signing_identities=[_identity("cert-1")])}
        certificates = [{"id": "cert-1", "name": "Cert", "expireDate": "2026-01-10T00:00:00+00:00"}]
        result = security_score(configs, ["A"], certificates, [], [], NOW)
        # signing_health_score=0 (expiring), env_var_usage_score=0 (no env vars)
        assert result["score"] == round(0 * 0.70 + 0 * 0.30)


class TestCombineOverallScore:
    def test_all_four_present(self):
        result = combine_overall_score(80, 70, 90, 60)
        assert result["overall_score"] == round(80 * 0.30 + 70 * 0.30 + 90 * 0.15 + 60 * 0.25)

    def test_security_missing_renormalizes_to_legacy_40_40_20_weights(self):
        # weight_total = 0.30+0.30+0.15 = 0.75 -> renormalized weights are
        # exactly 0.40/0.40/0.20, the pre-Security formula.
        result = combine_overall_score(80, 70, 90, None)
        assert result["overall_score"] == round(80 * 0.40 + 70 * 0.40 + 90 * 0.20)

    def test_discipline_missing_renormalizes_reliability_speed_security(self):
        result = combine_overall_score(80, None, 60, 40)
        weight_total = 0.30 + 0.15 + 0.25
        assert result["overall_score"] == round(80 * 0.30 / weight_total + 60 * 0.15 / weight_total + 40 * 0.25 / weight_total)

    def test_speed_missing_renormalizes_reliability_discipline_security(self):
        result = combine_overall_score(80, 70, None, 60)
        weight_total = 0.30 + 0.30 + 0.25
        assert result["overall_score"] == round(80 * 0.30 / weight_total + 70 * 0.30 / weight_total + 60 * 0.25 / weight_total)

    def test_only_reliability_available(self):
        result = combine_overall_score(80, None, None, None)
        assert result["overall_score"] == 80

    def test_label_breakpoints(self):
        cases = [(80, "Optimizing"), (65, "Advancing"), (45, "Practicing"), (44, "Developing"), (0, "Developing")]
        for score, expected_label in cases:
            result = combine_overall_score(score, score, score, score)
            assert result["overall_score"] == score
            assert result["label"] == expected_label


class TestTopImprovements:
    def test_flaky_profiles_flagged_as_critical(self):
        builds = [
            _build(profile="A", status=0, commit="shared"),
            _build(profile="A", status=1, commit="shared"),
        ]
        result = top_improvements(builds, ["A"], [], [], {"A": True})
        assert result[0] == {"check": "resolve_flaky_profiles", "severity": "critical", "profiles": ["A"]}

    def test_outlier_duration_only_flagged_against_same_platform(self):
        builds = [_build(profile="A", os_=1), _build(profile="B", os_=1), _build(profile="C", os_=2)]
        duration_rows = [
            {"profile": "A", "p50": 10, "ratio": 1.2},
            {"profile": "B", "p50": 50, "ratio": 1.2},  # iOS outlier vs A
            {"profile": "C", "p50": 100, "ratio": 1.2},  # lone Android profile, no comparison possible
        ]
        result = top_improvements(builds, ["A", "B", "C"], duration_rows, [], {})
        outlier_items = [i for i in result if i["check"] == "outlier_build_duration"]
        assert outlier_items == [{"check": "outlier_build_duration", "severity": "critical", "profiles": ["B"]}]

    def test_custom_script_and_versioning_advisories_from_workflow_quality_issues(self):
        issues = [
            {"check": "custom_script_not_from_git", "severity": "advisory", "profile": "A", "workflow": "WF", "count": 1},
            {"check": "versioning_not_automated", "severity": "critical", "profile": "B", "workflow": "WF"},
        ]
        result = top_improvements([], ["A", "B"], [], issues, {"A": True, "B": True})
        assert {"check": "custom_script_not_from_git", "severity": "advisory", "profiles": ["A"]} in result
        assert {"check": "versioning_not_automated", "severity": "advisory", "profiles": ["B"]} in result

    def test_pr_workflow_not_configured_lists_missing_profiles(self):
        result = top_improvements([], ["A", "B"], [], [], {"A": True, "B": False})
        assert {"check": "pr_workflow_not_configured", "severity": "advisory", "profiles": ["B"]} in result

    def test_pr_workflow_unknown_status_not_flagged(self):
        # B's triggers fetch failed (unknown) -- must not be flagged as
        # "not configured", which would be a false signal.
        result = top_improvements([], ["A", "B"], [], [], {"A": True, "B": None})
        assert not any(i["check"] == "pr_workflow_not_configured" for i in result)

    def test_no_issues_yields_empty_list(self):
        assert top_improvements([], ["A"], [], [], {"A": True}) == []

    def test_profile_with_unresolvable_os_skipped_from_outlier_check(self):
        builds = [_build(profile="A", os_=1)]  # "B" has no build records at all -> no os
        duration_rows = [
            {"profile": "A", "p50": 10, "ratio": 1.2},
            {"profile": "B", "p50": 50, "ratio": 1.2},
        ]
        result = top_improvements(builds, ["A", "B"], duration_rows, [], {})
        assert not any(i["check"] == "outlier_build_duration" for i in result)

    def test_priority_order_is_critical_then_advisory(self):
        builds = [
            _build(profile="A", status=0, commit="shared"),
            _build(profile="A", status=1, commit="shared"),
        ]
        issues = [{"check": "versioning_not_automated", "severity": "critical", "profile": "A", "workflow": "WF"}]
        result = top_improvements(builds, ["A"], [], issues, {"A": False})
        severities = [item["severity"] for item in result]
        assert severities == sorted(severities, key=lambda s: s != "critical")

    def test_expiring_signing_identities_flagged_as_critical(self):
        security = {
            "expiring_soon": [{"profiles": ["A"]}, {"profiles": ["B"]}],
            "profiles_without_env_vars": [],
        }
        result = top_improvements([], ["A", "B"], [], [], {}, security)
        assert {"check": "signing_identity_expiring_soon", "severity": "critical", "profiles": ["A", "B"]} in result

    def test_missing_env_vars_flagged_as_advisory(self):
        security = {"expiring_soon": [], "profiles_without_env_vars": ["C"]}
        result = top_improvements([], ["A", "B", "C"], [], [], {}, security)
        assert {"check": "environment_variables_not_configured", "severity": "advisory", "profiles": ["C"]} in result

    def test_no_security_data_yields_no_security_rules(self):
        result = top_improvements([], ["A"], [], [], {}, None)
        assert not any(i["check"] in ("signing_identity_expiring_soon", "environment_variables_not_configured") for i in result)
