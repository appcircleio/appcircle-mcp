"""Get build status tool."""

from typing import Dict, Any

from ...mcp_instance import mcp
from ...core.api_client import ApiClient
from ...core.error_handler import handle_api_error
from ...core.logger import logger
from ...schemas.responses import success_response

TOOL_NAME = "get_build_status"


@mcp.tool()
async def get_build_status(commit_id: str, build_id: str) -> Dict[str, Any]:
    """
    Get the status of a build.

    Returns the current status code for the given build under the given commit.

    Args:
        commit_id: The commit ID (UUID).
        build_id: The build ID (UUID).

    Returns:
        Standard envelope (see docs/tool_contract.md):
        - Success: success (true), data ({"status": <int>}), meta (empty).
          Status codes: 0=Success, 1=Failed, 2=Canceled, 3=Timeout,
          90=Waiting, 91=Running, 92=Completing, 99=Unknown.
        - Error: success (false), error (tool, type, message, details).

    Examples:
        Get build status: get_build_status(commit_id="commit-uuid", build_id="build-uuid")
    """
    try:
        logger.debug(f"Fetching build status - commit_id: {commit_id}, build_id: {build_id}")

        api_client = ApiClient()
        response = await api_client.get(
            f"/build/v2/commits/{commit_id}/builds/{build_id}/status"
        )

        data = response if isinstance(response, dict) else {}

        logger.info(
            f"Successfully retrieved build status for commit {commit_id}, build {build_id}"
        )

        return success_response(data=data, meta={})

    except Exception as e:
        logger.error(f"Failed to get build status: {str(e)}")
        return handle_api_error(e, TOOL_NAME)
