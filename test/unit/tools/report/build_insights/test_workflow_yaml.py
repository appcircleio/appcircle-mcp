"""Unit tests for build-insights workflow YAML fetch/parse helpers (respx-mocked)."""

import pytest
from httpx import Response

from src.core.api_client import ApiClient
from src.tools.report.build_insights.workflow_yaml import (
    _first_configured_workflow_id,
    fetch_profile_triggers,
    fetch_profile_workflow_yaml,
    fetch_workflow_list,
    fetch_workflow_yaml,
    find_workflow_id,
    has_pr_workflow_configured,
    resolve_push_pr_workflow_names,
)

# A trimmed, anonymized workflowDocument example.
REAL_LIKE_WORKFLOW_DOCUMENT = """
directories:
  - AC_SOURCE
  - AC_OUTPUT_DIR
steps:
  - componentType: appcircle_git_clone
    componentVersion: 1.1.*
    stepName: Git Clone
    enabled: true
  - componentType: appcircle_custom_script
    stepName: Custom Script(1)
    enabled: false
  - componentType: appcircle_cocoapods
    stepName: Cocoapods Install
    enabled: true
  - componentType: appcircle_ios_build_sign
    stepName: Xcodebuild for Devices
    enabled: true
  - componentType: appcircle_export_build_artifacts
    stepName: Export Build Artifacts
    enabled: true
"""


def _build(profile="A", workflow="Default Push Workflow", trigger=2):
    return {"buildProfileName": profile, "workflowName": workflow, "triggerCategory": trigger}


class TestResolvePushPrWorkflowNames:
    def test_resolves_both_from_trigger_category(self):
        curr_builds = [
            _build(workflow="Default Push Workflow", trigger=2),
            _build(workflow="Default Push Workflow", trigger=2),
            _build(workflow="Default PR Workflow", trigger=1),
            _build(workflow="Custom", trigger=0),  # manual, ignored
        ]
        push, pr = resolve_push_pr_workflow_names(curr_builds, "A")
        assert push == "Default Push Workflow"
        assert pr == "Default PR Workflow"

    def test_none_when_trigger_category_never_occurred(self):
        curr_builds = [_build(trigger=0)]
        assert resolve_push_pr_workflow_names(curr_builds, "A") == (None, None)

    def test_most_common_breaks_ties(self):
        curr_builds = [
            _build(workflow="Workflow A", trigger=2),
            _build(workflow="Workflow A", trigger=2),
            _build(workflow="Workflow B", trigger=2),
        ]
        push, _ = resolve_push_pr_workflow_names(curr_builds, "A")
        assert push == "Workflow A"

    def test_other_profiles_ignored(self):
        curr_builds = [_build(profile="B", trigger=2)]
        assert resolve_push_pr_workflow_names(curr_builds, "A") == (None, None)


class TestFindWorkflowId:
    def test_finds_matching_workflow_id(self):
        workflows = [{"id": "1", "workflowName": "A"}, {"id": "2", "workflowName": "B"}]
        assert find_workflow_id(workflows, "B") == "2"

    def test_none_when_not_found(self):
        workflows = [{"id": "1", "workflowName": "A"}]
        assert find_workflow_id(workflows, "Missing") is None


@pytest.mark.asyncio
class TestFetchWorkflowList:
    async def test_returns_raw_list_response_as_is(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=[{"id": "1", "workflowName": "A"}])
        )
        async with ApiClient() as api_client:
            workflows = await fetch_workflow_list(api_client, "p1")
        assert workflows == [{"id": "1", "workflowName": "A"}]

    async def test_normalizes_dict_wrapped_response(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json={"data": [{"id": "1", "workflowName": "A"}]})
        )
        async with ApiClient() as api_client:
            workflows = await fetch_workflow_list(api_client, "p1")
        assert workflows == [{"id": "1", "workflowName": "A"}]

    async def test_unrecognized_response_returns_empty_list(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_workflow_list(api_client, "p1") == []


@pytest.mark.asyncio
class TestFetchWorkflowYaml:
    async def test_parses_steps_from_real_like_document(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(
            return_value=Response(200, json={
                "id": "w1", "workflowName": "Default Push Workflow",
                "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT,
            })
        )
        async with ApiClient() as api_client:
            result = await fetch_workflow_yaml(api_client, "p1", "w1")

        assert result["workflow_name"] == "Default Push Workflow"
        component_types = [s["component_type"] for s in result["steps"]]
        assert component_types == [
            "appcircle_git_clone", "appcircle_custom_script", "appcircle_cocoapods",
            "appcircle_ios_build_sign", "appcircle_export_build_artifacts",
        ]

    async def test_disabled_step_marked_not_enabled(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(
            return_value=Response(200, json={
                "workflowName": "wf", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT,
            })
        )
        async with ApiClient() as api_client:
            result = await fetch_workflow_yaml(api_client, "p1", "w1")

        custom_script_step = next(s for s in result["steps"] if s["component_type"] == "appcircle_custom_script")
        assert custom_script_step["enabled"] is False

    async def test_missing_workflow_document_returns_none(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(
            return_value=Response(200, json={"workflowName": "wf", "lastUsedTime": "2026-01-01T00:00:00Z"})
        )
        async with ApiClient() as api_client:
            assert await fetch_workflow_yaml(api_client, "p1", "w1") is None

    async def test_unparseable_yaml_returns_none(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(
            return_value=Response(200, json={"workflowName": "wf", "workflowDocument": "key: [unclosed"})
        )
        async with ApiClient() as api_client:
            assert await fetch_workflow_yaml(api_client, "p1", "w1") is None

    async def test_yaml_that_parses_to_non_dict_returns_none(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(
            return_value=Response(200, json={"workflowName": "wf", "workflowDocument": "- just\n- a\n- list\n"})
        )
        async with ApiClient() as api_client:
            assert await fetch_workflow_yaml(api_client, "p1", "w1") is None

    async def test_non_dict_response_returns_none(self, mocked_api):
        mocked_api.get("/build/v2/profiles/p1/workflows/w1").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_workflow_yaml(api_client, "p1", "w1") is None


@pytest.mark.asyncio
class TestFetchProfileWorkflowYaml:
    async def test_returns_none_none_when_no_trigger_activity(self, mocked_api):
        curr_builds = [_build(trigger=0)]
        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1")
        assert (push, pr) == (None, None)
        assert len(mocked_api.calls) == 0  # no fetch attempted at all

    async def test_fetches_resolved_push_and_pr_workflows(self, mocked_api):
        curr_builds = [
            _build(workflow="Push WF", trigger=2),
            _build(workflow="PR WF", trigger=1),
        ]
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=[
                {"id": "push-id", "workflowName": "Push WF"},
                {"id": "pr-id", "workflowName": "PR WF"},
            ])
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Push WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/pr-id").mock(
            return_value=Response(200, json={"workflowName": "PR WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )

        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1")

        assert push["workflow_name"] == "Push WF"
        assert pr["workflow_name"] == "PR WF"

    async def test_unresolved_workflow_id_yields_none_for_that_side(self, mocked_api):
        curr_builds = [_build(workflow="Push WF", trigger=2)]  # no PR activity
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=[{"id": "push-id", "workflowName": "Push WF"}])
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Push WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )

        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1")

        assert push is not None
        assert pr is None

    async def test_trigger_config_fallback_resolves_all_manual_profile(self, mocked_api):
        """A profile triggered only manually this period has no Push/PR
        `triggerCategory` in build history at all, so identity resolves
        from trigger config instead. No workflow-list call is needed here:
        the trigger config already gives the `workflowId` directly."""
        curr_builds = [_build(trigger=0)]
        triggers = {
            "pushSettings": [{"workflowId": "push-id"}],
            "pullRequestSettings": [{"workflowId": "pr-id"}],
        }
        mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Push WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )
        mocked_api.get("/build/v2/profiles/p1/workflows/pr-id").mock(
            return_value=Response(200, json={"workflowName": "PR WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )

        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1", triggers)

        assert push["workflow_name"] == "Push WF"
        assert pr["workflow_name"] == "PR WF"
        workflow_list_calls = [c for c in mocked_api.calls if str(c.request.url).endswith("/workflows/")]
        assert workflow_list_calls == []  # not needed -- trigger config already gave the id

    async def test_history_resolution_takes_priority_over_trigger_config(self, mocked_api):
        """If build history already resolved a side, the trigger-config
        fallback must not override it with a different workflow."""
        curr_builds = [_build(workflow="Push WF", trigger=2)]
        triggers = {"pushSettings": [{"workflowId": "other-id"}], "pullRequestSettings": []}
        mocked_api.get("/build/v2/profiles/p1/workflows/").mock(
            return_value=Response(200, json=[{"id": "push-id", "workflowName": "Push WF"}])
        )
        workflow_route = mocked_api.get("/build/v2/profiles/p1/workflows/push-id").mock(
            return_value=Response(200, json={"workflowName": "Push WF", "workflowDocument": REAL_LIKE_WORKFLOW_DOCUMENT})
        )

        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1", triggers)

        assert push["workflow_name"] == "Push WF"
        assert pr is None
        assert len(workflow_route.calls) == 1

    async def test_no_history_and_no_trigger_config_yields_none_none(self, mocked_api):
        """A profile with no Push/PR activity this period and no Push/PR
        workflow configured at all -- genuinely nothing to resolve."""
        curr_builds = [_build(trigger=0)]
        triggers = {"pushSettings": [], "pullRequestSettings": [], "tagSettings": []}

        async with ApiClient() as api_client:
            push, pr = await fetch_profile_workflow_yaml(api_client, curr_builds, "A", "p1", triggers)

        assert (push, pr) == (None, None)
        assert len(mocked_api.calls) == 0


@pytest.mark.asyncio
class TestFetchProfileTriggers:
    async def test_parses_real_like_response(self, mocked_api):
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(
            return_value=Response(200, json={
                "pullRequestSettings": [
                    {"sourceBranches": ["develop"], "targetBranch": "master", "workflowId": "wf-pr", "configurationId": "cfg-1", "defaultSettingBranch": None}
                ],
                "pushSettings": [
                    {"branchName": "main", "workflowId": "wf-push", "configurationId": "cfg-1", "defaultSettingBranch": None}
                ],
                "tagSettings": [],
            })
        )
        async with ApiClient() as api_client:
            triggers = await fetch_profile_triggers(api_client, "p1")

        assert triggers["pullRequestSettings"][0]["workflowId"] == "wf-pr"
        assert triggers["pushSettings"][0]["workflowId"] == "wf-push"

    async def test_non_dict_response_returns_none(self, mocked_api):
        mocked_api.get("/build/v1/profiles/p1/triggers").mock(return_value=Response(200, json="oops"))
        async with ApiClient() as api_client:
            assert await fetch_profile_triggers(api_client, "p1") is None


class TestFirstConfiguredWorkflowId:
    def test_returns_first_rules_workflow_id(self):
        rules = [{"workflowId": "wf-1"}, {"workflowId": "wf-2"}]
        assert _first_configured_workflow_id(rules) == "wf-1"

    def test_none_when_rules_empty(self):
        assert _first_configured_workflow_id([]) is None

    def test_none_when_rules_is_none(self):
        assert _first_configured_workflow_id(None) is None


class TestHasPrWorkflowConfigured:
    def test_true_when_pull_request_settings_non_empty(self):
        assert has_pr_workflow_configured({"pullRequestSettings": [{"workflowId": "wf-pr"}]}) is True

    def test_false_when_pull_request_settings_empty(self):
        assert has_pr_workflow_configured({"pullRequestSettings": [], "pushSettings": [{"workflowId": "wf-push"}]}) is False

    def test_false_when_pull_request_settings_missing(self):
        assert has_pr_workflow_configured({"pushSettings": []}) is False

    def test_false_when_triggers_is_none(self):
        assert has_pr_workflow_configured(None) is False
