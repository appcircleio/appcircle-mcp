"""Get build profile workflows tool."""

from typing import Dict, Any, List

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_build_profile_workflows"


def _normalize_workflows_response(response: Any) -> List[Dict[str, Any]]:
    """Return list of workflows from API response (list or wrapper)."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("data") or response.get("items") or response.get("workflows") or []
    return []


@mcp.tool()
async def get_build_profile_workflows(profile_id: str) -> Dict[str, Any]:
    """
    Get workflows for a build profile by profile ID.

    Returns the list of workflows associated with the given build profile,
    including workflow id, name, and last used time.

    Args:
        profile_id: The build profile ID (e.g. UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data (list of workflow objects), meta (count).
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get workflows for a profile: get_build_profile_workflows(profile_id="uuid-here")
    """
    try:
        logger.debug(f"Fetching build profile workflows - profile_id: {profile_id}")

        api_client = ApiClient()
        response = await api_client.get(f"/build/v2/profiles/{profile_id}/workflows/")

        workflows = _normalize_workflows_response(response)
        count = len(workflows)

        logger.info(f"Successfully retrieved {count} workflows for build profile {profile_id}")

        return success_response(data=workflows, meta={"count": count})

    except Exception as e:
        logger.error(f"Failed to get build profile workflows: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
