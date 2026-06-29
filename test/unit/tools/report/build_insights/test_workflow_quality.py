"""Unit tests for build-insights Workflow Quality compute functions.
Pure-function tests against fabricated steps/build records -- no HTTP involved."""

from src.tools.report.build_insights.workflow_quality import (
    ANDROID_OS,
    IOS_OS,
    best_practice_checks,
    detect_os,
    group_present,
    score_workflow,
)


def _step(component_type, enabled=True, step_name=""):
    return {"component_type": component_type, "step_name": step_name, "enabled": enabled}


FULL_IOS_PUSH_STEPS = [
    _step("appcircle_git_clone"),
    _step("appcircle_cocoapods"),
    _step("appcircle_ios_build_sign"),
    _step("appcircle_export_build_artifacts"),
    _step("appcircle_cache_pull"),
    _step("appcircle_cache_push"),
    _step("appcircle_ios_build_version_increment"),
    _step("appcircle_ios_test"),
    _step("appcircle_swiftlint"),
    _step("appcircle_snyk_scan_secure"),
    _step("appcircle_filesize"),
    _step("appcircle_azure_boards"),
    _step("appcircle_ios_kobil_appshield_scanner"),
]

FULL_ANDROID_PUSH_STEPS = [
    _step("appcircle_git_clone"),
    _step("appcircle_android_build"),
    _step("appcircle_android_sign"),
    _step("appcircle_export_build_artifacts"),
    _step("appcircle_cache_pull"),
    _step("appcircle_cache_push"),
    _step("appcircle_android_build_version_increment"),
    _step("appcircle_sonarqube"),
    _step("appcircle_snyk_scan_secure"),
    _step("appcircle_filesize"),
    _step("appcircle_jira"),
    _step("appcircle_appsweep"),
]


def _build(profile="A", os_code=IOS_OS):
    return {"buildProfileName": profile, "os": os_code}


class TestDetectOs:
    def test_finds_os_from_matching_build(self):
        assert detect_os([_build(os_code=IOS_OS)], "A") == IOS_OS

    def test_none_when_no_matching_profile(self):
        assert detect_os([_build(profile="B")], "A") is None

    def test_none_when_os_field_missing(self):
        assert detect_os([{"buildProfileName": "A", "os": None}], "A") is None


class TestGroupPresent:
    def test_true_when_enabled_step_matches(self):
        steps = [_step("appcircle_git_clone")]
        assert group_present(steps, {"appcircle_git_clone"}) is True

    def test_false_when_only_disabled_step_matches(self):
        steps = [_step("appcircle_git_clone", enabled=False)]
        assert group_present(steps, {"appcircle_git_clone"}) is False

    def test_false_when_no_step_matches(self):
        steps = [_step("appcircle_custom_script")]
        assert group_present(steps, {"appcircle_git_clone"}) is False


class TestScoreWorkflow:
    def test_full_marks_for_fully_compliant_ios_push_workflow(self):
        score = score_workflow(FULL_IOS_PUSH_STEPS, IOS_OS, is_push=True)
        assert score["tier1_score"] == 60
        assert score["tier2_score"] == 30
        assert score["tier3_score"] == 10
        assert score["total_score"] == 100
        assert score["missing_groups"] == []

    def test_full_marks_for_fully_compliant_android_push_workflow(self):
        score = score_workflow(FULL_ANDROID_PUSH_STEPS, ANDROID_OS, is_push=True)
        assert score["total_score"] == 100
        assert score["missing_groups"] == []

    def test_bare_workflow_gets_partial_tier1_and_zero_elsewhere(self):
        steps = [_step("appcircle_git_clone"), _step("appcircle_export_build_artifacts")]
        score = score_workflow(steps, IOS_OS, is_push=True)
        assert score["tier2_score"] == 0
        assert score["tier3_score"] == 0
        assert {g["group"] for g in score["missing_groups"]} >= {"Dependencies", "Build"}

    def test_pr_workflow_excludes_push_only_groups_from_missing(self):
        steps = [_step("appcircle_git_clone"), _step("appcircle_cocoapods"), _step("appcircle_ios_build_sign"), _step("appcircle_export_build_artifacts")]
        pr_score = score_workflow(steps, IOS_OS, is_push=False)
        push_score = score_workflow(steps, IOS_OS, is_push=True)
        pr_missing_names = {g["group"] for g in pr_score["missing_groups"]}
        push_missing_names = {g["group"] for g in push_score["missing_groups"]}
        assert "Versioning" not in pr_missing_names
        assert "Binary security" not in pr_missing_names
        assert "Versioning" in push_missing_names
        assert "Binary security" in push_missing_names
        # Tier1 (no push-only groups) is identical either way
        assert pr_score["tier1_score"] == push_score["tier1_score"] == 60

    def test_returns_none_for_unrecognized_os(self):
        assert score_workflow(FULL_IOS_PUSH_STEPS, None, is_push=True) is None
        assert score_workflow(FULL_IOS_PUSH_STEPS, 99, is_push=True) is None

    def test_completely_empty_workflow_scores_zero(self):
        score = score_workflow([], IOS_OS, is_push=True)
        assert score["total_score"] == 0
        assert len(score["missing_groups"]) == 13  # every iOS group


class TestBestPracticeChecks:
    def test_flags_versioning_not_automated_when_missing(self):
        steps = [_step("appcircle_git_clone")]
        issues = best_practice_checks("A", IOS_OS, "Push WF", steps, None, None)
        assert any(i["check"] == "versioning_not_automated" for i in issues)

    def test_no_versioning_issue_when_automated(self):
        steps = [_step("appcircle_ios_build_version_increment")]
        issues = best_practice_checks("A", IOS_OS, "Push WF", steps, None, None)
        assert not any(i["check"] == "versioning_not_automated" for i in issues)

    def test_no_versioning_check_without_push_steps(self):
        issues = best_practice_checks("A", IOS_OS, None, None, "PR WF", [_step("appcircle_git_clone")])
        assert not any(i["check"] == "versioning_not_automated" for i in issues)

    def test_flags_inline_custom_script_on_push(self):
        steps = [_step("appcircle_custom_script")]
        issues = best_practice_checks("A", IOS_OS, "Push WF", steps, None, None)
        script_issues = [i for i in issues if i["check"] == "custom_script_not_from_git"]
        assert len(script_issues) == 1
        assert script_issues[0]["count"] == 1
        assert script_issues[0]["workflow"] == "Push WF"

    def test_flags_inline_custom_script_on_both_push_and_pr_separately(self):
        push_steps = [_step("appcircle_custom_script")]
        pr_steps = [_step("appcircle_custom_script"), _step("appcircle_custom_script")]
        issues = best_practice_checks("A", IOS_OS, "Push WF", push_steps, "PR WF", pr_steps)
        script_issues = {i["workflow"]: i["count"] for i in issues if i["check"] == "custom_script_not_from_git"}
        assert script_issues == {"Push WF": 1, "PR WF": 2}

    def test_custom_script_from_git_is_not_flagged(self):
        steps = [_step("appcircle_custom_script_from_git")]
        issues = best_practice_checks("A", IOS_OS, "Push WF", steps, None, None)
        assert not any(i["check"] == "custom_script_not_from_git" for i in issues)

    def test_disabled_inline_script_is_not_flagged(self):
        steps = [_step("appcircle_custom_script", enabled=False)]
        issues = best_practice_checks("A", IOS_OS, "Push WF", steps, None, None)
        assert not any(i["check"] == "custom_script_not_from_git" for i in issues)

    def test_no_issues_for_fully_compliant_workflow(self):
        issues = best_practice_checks("A", IOS_OS, "Push WF", FULL_IOS_PUSH_STEPS, None, None)
        assert issues == []
