"""Fetch and parse workflow YAML for the build-insights report's Workflow
Quality section, and resolve which workflow is "the Push one" / "the PR one"
for a profile.

There is no `triggers` field in the workflow list/detail response or inside
the `workflowDocument` YAML. Push/PR identity is resolved from build history
first: every build record carries `workflowName` and `triggerCategory`
(0=Manual, 1=PR Trigger, 2=Push Trigger, 3=Tag Trigger), so the most-common
`workflowName` among a profile's Push-triggered (or PR-triggered) builds this
period is that profile's Push (or PR) workflow. If a profile is triggered
only manually this period, that heuristic resolves nothing, and
`fetch_profile_workflow_yaml` falls back to the trigger-config endpoint's
`workflowId` for whichever side build history couldn't resolve.
"""

import asyncio
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ....core.api_client import ApiClient

PUSH_TRIGGER_CATEGORY = 2
PR_TRIGGER_CATEGORY = 1


def resolve_push_pr_workflow_names(
    curr_builds: List[Dict[str, Any]],
    profile: str,
) -> Tuple[Optional[str], Optional[str]]:
    """(push_workflow_name, pr_workflow_name) for `profile`. `None` for either
    if that trigger category never occurred for this profile this period --
    that workflow identity simply can't be resolved this run, not faked."""

    def most_common_workflow(trigger_category: int) -> Optional[str]:
        names = Counter(
            build["workflowName"]
            for build in curr_builds
            if build["buildProfileName"] == profile
            and build.get("triggerCategory") == trigger_category
            and build.get("workflowName")
        )
        return names.most_common(1)[0][0] if names else None

    return most_common_workflow(PUSH_TRIGGER_CATEGORY), most_common_workflow(PR_TRIGGER_CATEGORY)


async def fetch_workflow_list(api_client: ApiClient, profile_id: str) -> List[Dict[str, Any]]:
    """GET /build/v2/profiles/{profile_id}/workflows/ -- a bare list of
    {id, workflowName, lastUsedTime, ...}."""
    response = await api_client.get(f"/build/v2/profiles/{profile_id}/workflows")
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        workflows = response.get("data") or response.get("items") or response.get("workflows") or []
        return workflows if isinstance(workflows, list) else []
    return []


def find_workflow_id(workflows: List[Dict[str, Any]], workflow_name: str) -> Optional[str]:
    for workflow in workflows:
        if workflow.get("workflowName") == workflow_name:
            return workflow.get("id")
    return None


async def fetch_workflow_yaml(
    api_client: ApiClient,
    profile_id: str,
    workflow_id: str,
) -> Optional[Dict[str, Any]]:
    """GET .../workflows/{workflow_id}, parse `workflowDocument` YAML.

    Returns {"workflow_name": str, "steps": [{"component_type", "step_name",
    "enabled"}]}, or `None` if `workflowDocument` is missing or unparseable --
    gated, not fatal, since the existing integration test for this endpoint
    only weakly asserts `workflowDocument`'s presence.
    """
    response = await api_client.get(f"/build/v2/profiles/{profile_id}/workflows/{workflow_id}")
    workflow = response.get("data") or response.get("workflow") or response if isinstance(response, dict) else None
    if not isinstance(workflow, dict):
        return None

    document = workflow.get("workflowDocument")
    if not document:
        return None
    try:
        parsed = yaml.safe_load(document)
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return None

    raw_steps = parsed.get("steps") or []
    steps = [
        {
            "component_type": step.get("componentType"),
            "step_name": step.get("stepName"),
            "enabled": step.get("enabled", True) is not False,
        }
        for step in raw_steps
        if isinstance(step, dict)
    ]
    return {"workflow_name": workflow.get("workflowName"), "steps": steps}


async def fetch_profile_triggers(api_client: ApiClient, profile_id: str) -> Optional[Dict[str, Any]]:
    """GET /build/v1/profiles/{profile_id}/triggers -- a bare
    {"pullRequestSettings", "pushSettings", "tagSettings"} dict, each a list
    of rules with a `workflowId`. Used for Maturity Assessment's "PR
    workflow configured" check, and as `fetch_profile_workflow_yaml`'s
    fallback identity source.
    """
    response = await api_client.get(f"/build/v1/profiles/{profile_id}/triggers")
    return response if isinstance(response, dict) else None


def has_pr_workflow_configured(triggers: Optional[Dict[str, Any]]) -> bool:
    if not triggers:
        return False
    return bool(triggers.get("pullRequestSettings"))


def _first_configured_workflow_id(rules: Optional[List[Dict[str, Any]]]) -> Optional[str]:
    """First rule's `workflowId` from a trigger-config list (`pushSettings`/
    `pullRequestSettings`). A profile's rules can route different branches to
    different workflows, but for "the Push/PR workflow" only one
    representative is needed to score."""
    if not rules:
        return None
    return rules[0].get("workflowId")


async def fetch_profile_workflow_yaml(
    api_client: ApiClient,
    curr_builds: List[Dict[str, Any]],
    profile: str,
    profile_id: str,
    triggers: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Resolve and fetch the parsed Push and PR workflow YAML for one profile.

    Returns (push_workflow, pr_workflow), each `None` if that workflow's
    identity couldn't be resolved (from build history or `triggers`) this
    period or its YAML wasn't fetchable.
    """
    push_name, pr_name = resolve_push_pr_workflow_names(curr_builds, profile)

    push_id = pr_id = None
    if push_name or pr_name:
        workflows = await fetch_workflow_list(api_client, profile_id)
        push_id = find_workflow_id(workflows, push_name) if push_name else None
        pr_id = find_workflow_id(workflows, pr_name) if pr_name else None

    # Fall back to the trigger-config endpoint's `workflowId` for whichever
    # side build history didn't resolve. History takes priority when it
    # already resolved a side.
    if triggers:
        if push_id is None:
            push_id = _first_configured_workflow_id(triggers.get("pushSettings"))
        if pr_id is None:
            pr_id = _first_configured_workflow_id(triggers.get("pullRequestSettings"))

    if push_id is None and pr_id is None:
        return None, None

    async def fetch_or_none(workflow_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not workflow_id:
            return None
        return await fetch_workflow_yaml(api_client, profile_id, workflow_id)

    push_workflow, pr_workflow = await asyncio.gather(fetch_or_none(push_id), fetch_or_none(pr_id))
    return push_workflow, pr_workflow
