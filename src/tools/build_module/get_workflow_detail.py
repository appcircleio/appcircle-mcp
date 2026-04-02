"""Get workflow detail tool."""

from typing import Dict, Any

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_workflow_detail"


@mcp.tool()
async def get_workflow_detail(
    profile_id: str,
    workflow_id: str,
) -> Dict[str, Any]:
    """
    Get a single workflow by build profile ID and workflow ID.

    Returns the workflow with the given IDs, including workflow name,
    workflow document (YAML definition of steps), and last used time.

    Args:
        profile_id: The build profile ID (e.g. UUID).
        workflow_id: The workflow ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (workflow object with id, profileId, workflowName, workflowDocument, lastUsedTime, etc.), meta (empty).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get workflow detail: get_workflow_detail(profile_id="uuid", workflow_id="workflow-uuid")
    """
    try:
        logger.debug(
            f"Fetching workflow detail - profile_id: {profile_id}, workflow_id: {workflow_id}"
        )

        api_client = ApiClient()
        response = await api_client.get(
            f"/build/v2/profiles/{profile_id}/workflows/{workflow_id}"
        )

        if isinstance(response, dict):
            data = response.get("data") or response.get("workflow") or response
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}

        logger.info(
            f"Successfully retrieved workflow detail for {profile_id}/{workflow_id}"
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get workflow detail: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
