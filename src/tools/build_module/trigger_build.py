"""Trigger build tool (write/action)."""

from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.validation import path_segment
from ...core.error_handler import handle_write_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "trigger_build"


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )
)
async def trigger_build(
    profile_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    branch_name: Optional[str] = None,
    commit_id: Optional[str] = None,
    configuration_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    SIDE EFFECT: Starts a new real build run on Appcircle. This is a write/action
    tool -- it queues an actual build (consuming build minutes/credits), it does
    not just read data.

    Trigger a new build either on a branch (latest synced commit) or for one
    specific commit. Exactly one of these two modes must be used:
    - Branch mode (default): requires profile_id and workflow_id. branch_name is
      optional (falls back to the profile's default branch if omitted).
    - Commit mode: requires commit_id (the commit's own id, e.g. from
      get_last_commit/get_commits_by_branch/get_commit_details -- not the git
      hash). workflow_id is optional in this mode (falls back to the last-used
      or default workflow for that commit's profile if omitted). profile_id and
      branch_name are not used in this mode (the commit_id already scopes to one
      profile/branch) and must not be given together with commit_id/branch_name
      respectively.

    No environment-variable overrides can be passed through this tool.

    Args:
        profile_id: The build profile ID (e.g. UUID). Required in branch mode; unused in commit mode.
        workflow_id: The workflow ID (e.g. UUID). Required in branch mode. Optional in commit
            mode (uses the last-used/default workflow for that commit if omitted).
        branch_name: Optional branch name (e.g. "main"). Branch mode only; falls back to the
            profile's default branch if omitted. Must not be given together with commit_id.
        commit_id: The commit's own ID (not its git hash) to trigger a build for a specific
            commit instead of the latest one on a branch. Must not be given together with branch_name.
        configuration_id: Optional build configuration ID (e.g. UUID) to use instead of the
            branch/commit's default configuration.

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"taskId": <uuid>, "queueItemId": <uuid>}), meta
          (trigger_mode, profile_id, workflow_id, branch_name, commit_id, configuration_id).
        - Error: success (false), error (tool, type, message, details). type is validation_error
          for a bad combination of arguments, or invalid_state (HTTP 409/422) when the target
          branch/commit/workflow is not in a state that allows triggering a build right now.

    Examples:
        Trigger on a branch's latest commit: trigger_build(profile_id="p-uuid", workflow_id="wf-uuid", branch_name="main")
        Trigger on the profile's default branch: trigger_build(profile_id="p-uuid", workflow_id="wf-uuid")
        Trigger for a specific commit: trigger_build(commit_id="commit-uuid")
        Trigger for a specific commit with an explicit workflow: trigger_build(commit_id="commit-uuid", workflow_id="wf-uuid")
    """
    try:
        if commit_id is not None and branch_name is not None:
            raise ValueError("Provide either branch_name or commit_id, not both.")

        if commit_id is None:
            if profile_id is None:
                raise ValueError("profile_id is required when triggering by branch (commit_id not given).")
            if workflow_id is None:
                raise ValueError("workflow_id is required when triggering by branch (commit_id not given).")

        params: Dict[str, Any] = {}
        if configuration_id is not None:
            params["configurationId"] = configuration_id

        api_client = ApiClient()

        if commit_id is not None:
            trigger_mode = "commit"
            if workflow_id is not None:
                params["workflowId"] = workflow_id
                endpoint = f"/build/v3/commits/{path_segment(commit_id, 'commit_id')}/build/by-workflow"
            else:
                endpoint = f"/build/v3/commits/{path_segment(commit_id, 'commit_id')}/build"
            logger.debug(f"Triggering build (commit mode) - commit_id: {commit_id}, params: {params}")
            response = await api_client.post(endpoint, params=params)
        else:
            trigger_mode = "branch"
            if branch_name is not None:
                params["branchName"] = branch_name
            endpoint = f"/build/v2/profiles/{path_segment(profile_id, 'profile_id')}/workflow/{path_segment(workflow_id, 'workflow_id')}"
            logger.debug(
                f"Triggering build (branch mode) - profile_id: {profile_id}, "
                f"workflow_id: {workflow_id}, params: {params}"
            )
            response = await api_client.put(endpoint, json_data={}, params=params)

        data = response if isinstance(response, dict) else {}

        logger.info(f"Successfully triggered build ({trigger_mode} mode): {data}")

        meta = {
            "trigger_mode": trigger_mode,
            "profile_id": profile_id,
            "workflow_id": workflow_id,
            "branch_name": branch_name,
            "commit_id": commit_id,
            "configuration_id": configuration_id,
        }
        return success_response(data=data, meta=meta)

    except Exception as e:
        logger.error(f"Failed to trigger build: {str(e)}")
        return handle_write_api_error(e, TOOL_NAME)
